import copy

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone
from django.utils.formats import localize
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, can_proceed, transition

from . import constants, versionables
from .conditions import (
    Conditions,
    draft_is_locked,
    draft_is_not_locked,
    in_state,
    is_not_locked,
    user_can_change,
    user_can_publish,
    user_can_unlock,
)
from .conf import ALLOW_DELETING_VERSIONS, LOCK_VERSIONS
from .operations import send_post_version_operation, send_pre_version_operation

try:
    from djangocms_internalsearch.helpers import emit_content_change
except ImportError:
    emit_content_change = None


not_draft_error = _("Version is not a draft")
lock_error_message = _("Action Denied. The latest version is locked by {user}")
lock_draft_error_message = _("Action Denied. The draft version is locked by {user}")
permission_error_message = _("You do not have permission to perform this action")

def allow_deleting_versions(collector, field, sub_objs, using):
    if ALLOW_DELETING_VERSIONS:
        models.SET_NULL(collector, field, sub_objs, using)
    else:
        models.PROTECT(collector, field, sub_objs, using)


class VersionQuerySet(models.QuerySet):
    def get_for_content(self, content_object):
        """Returns Version object corresponding to provided content object
        """
        if hasattr(content_object, "_version_cache"):
            return content_object._version_cache
        versionable = versionables.for_content(content_object)
        version = self.get(
            object_id=content_object.pk, content_type__in=versionable.content_types
        )
        content_object._version_cache = version
        return version

    def filter_by_grouper(self, grouper_object):
        """Returns a list of Version objects for the provided grouper
        object
        """
        versionable = versionables.for_grouper(grouper_object)
        return self.filter_by_grouping_values(
            versionable, **{versionable.grouper_field_name: grouper_object}
        )

    def filter_by_grouping_values(self, versionable, **kwargs):
        """Returns a list of Version objects for the provided grouping
        values (unique grouper version list)
        """
        content_objects = versionable.for_grouping_values(**kwargs)
        return self.filter(
            object_id__in=content_objects, content_type__in=versionable.content_types
        )

    def filter_by_content_grouping_values(self, content):
        """Returns a list of Version objects for grouping values taken
        from provided content object. In other words:
        it uses the content instance property values as filter parameters
        """
        versionable = versionables.for_content(content)
        content_objects = versionable.for_content_grouping_values(content)
        return self.filter(
            object_id__in=content_objects, content_type__in=versionable.content_types
        )


class Version(models.Model):

    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))
    modified = models.DateTimeField(default=timezone.now, verbose_name=_("Modified"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("author")
    )
    number = models.CharField(max_length=11, verbose_name="#")
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="cms_versions"
    )
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey("content_type", "object_id")
    state = FSMField(
        default=constants.DRAFT,
        choices=constants.VERSION_STATES,
        verbose_name=_("status"),
        protected=True,
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Deleting a user removes the lock
        null=True,
        default=None,
        verbose_name=_("locked by"),
        related_name="locking_users",
    )
    visibility_start = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_("visible after"),
        help_text=_("Leave empty for immediate public visibility"),
    )

    visibility_end = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
        verbose_name=_("visible until"),
        help_text=_("Leave empty for unrestricted public visibility"),
    )

    source = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=allow_deleting_versions,
        verbose_name=_("source"),
    )
    objects = VersionQuerySet.as_manager()

    class Meta:
        unique_together = ("content_type", "object_id")
        permissions = (
            ("delete_versionlock", "Can unlock verision"),
        )

    def __str__(self):
        return f"Version #{self.pk}"

    def verbose_name(self):
        return _("Version #{number} ({state} {date})").format(
            number=self.number,
            state=dict(constants.VERSION_STATES)[self.state],
            date=localize(self.created, settings.DATETIME_FORMAT),
        )

    def short_name(self):
        state = dict(constants.VERSION_STATES)[self.state]
        if self.state == constants.PUBLISHED:
            if self.visibility_start and self.visibility_start > timezone.now():
                state = _("Pending")
            elif self.visibility_end and self.visibility_end < timezone.now():
                state = _("Expired")
        return _("Version #{number} ({state})").format(
            number=self.number, state=state
        )

    def locked_message(self):
        if self.locked_by:
            return _("Locked by %(user)s") % {"user": self.locked_by}
        return ""

    def delete(self, using=None, keep_parents=False):
        """Deleting a version deletes the grouper
        as well if we are deleting the last version."""

        def get_grouper_name(ContentModel, GrouperModel):
            for field in ContentModel._meta.fields:
                if getattr(field, "related_model", None) == GrouperModel:
                    return field.name

        grouper = self.grouper
        ContentModel = self.content._meta.model

        grouper_name = get_grouper_name(ContentModel, grouper._meta.model)
        querydict = {f"{grouper_name}__pk": grouper.pk}
        count = ContentModel._original_manager.filter(**querydict).count()

        self.content.delete()
        deleted = super().delete(using=using, keep_parents=keep_parents)
        deleted[1]["last"] = False
        if count == 1:
            grouper.delete()
            deleted[1]["last"] = True
        return deleted

    def save(self, **kwargs):
        created = not self.pk
        # On version creation
        if created:
            # trigger pre operation signal
            action_token = send_pre_version_operation(
                constants.OPERATION_DRAFT, version=self
            )
            # Set the version number
            self.number = self.make_version_number()
        if self.pk is None and self.state == constants.DRAFT:
            # A new draft version is locked by default
            if LOCK_VERSIONS and self.locked_by is None:
                # create a lock
                self.locked_by = self.created_by
        elif self.state != constants.DRAFT:
            # A any other state than draft has no lock, an existing lock should be removed
            self.locked_by = None

        super().save(**kwargs)
        # Only one draft version is allowed per unique grouping values.
        # Set all other drafts to archived
        if self.state == constants.DRAFT:
            if created:
                pks_for_grouping_values = self.versionable.for_content_grouping_values(
                    self.content
                ).values_list("pk", flat=True)
                to_archive = Version.objects.exclude(pk=self.pk).filter(
                    state=constants.DRAFT,
                    object_id__in=pks_for_grouping_values,
                    content_type=self.content_type,
                )
                for version in to_archive:
                    version.archive(self.created_by)
                on_draft_create = self.versionable.on_draft_create
                if on_draft_create:
                    on_draft_create(self)
                # trigger post operation signal
                send_post_version_operation(
                    constants.OPERATION_DRAFT, version=self, token=action_token
                )
            if emit_content_change:
                emit_content_change(self.content, created=created)

    def make_version_number(self):
        """
        Create a version number for each version
        """
        # Get the latest version object
        latest_version = (
            Version.objects.filter_by_content_grouping_values(self.content)
            .order_by("-pk")
            .first()
        )
        # If no previous version exists start at 1
        if not latest_version:
            return 1
        return int(latest_version.number) + 1

    @property
    def versionable(self):
        """Helper property to get the versionable for the content type
        of the version
        """
        return versionables.for_content(self.content)

    def convert_to_proxy(self):
        """Returns a copy of current Version object, but as an instance
        of its correct proxy model"""

        new_obj = copy.deepcopy(self)
        new_obj.__class__ = self.versionable.version_model_proxy
        return new_obj

    @property
    def grouper(self):
        """Helper property to get the grouper for the version
        """
        return getattr(self.content, self.versionable.grouper_field_name)

    @transaction.atomic
    def copy(self, created_by):
        """Creates a new Version object, with a copy of the related
        content object.
        Allows customization of how the content object will be copied
        when specified in cms_config.py

        This method needs to be run in a transaction due to the fact that if
        models are partially created in the copy method a version is not attached.
        It needs to be that if anything goes wrong we should roll back the entire task.
        We shouldn't leave this to package developers to know to add this feature
        because not doing so leaves the db and versioning in a corrupt state where
        content models exist without a version.
        """
        copy_function = versionables.for_content(self.content).copy_function
        new_content = copy_function(self.content)

        new_version = Version.objects.create(
            content=new_content, source=self, created_by=created_by,
            **({"locked_by": created_by} if LOCK_VERSIONS else {}),
        )
        return new_version

    check_archive = Conditions(
        [
            user_can_change(permission_error_message),
            in_state([constants.DRAFT], _("Version is not in draft state")),
            is_not_locked(lock_error_message),
        ]
    )

    def can_be_archived(self):
        return can_proceed(self._set_archive)

    def archive(self, user):
        """Change state to ARCHIVED"""
        # trigger pre operation signal
        action_token = send_pre_version_operation(
            constants.OPERATION_ARCHIVE, version=self
        )
        self._set_archive(user)
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.ARCHIVED,
            user=user,
        )
        on_archive = self.versionable.on_archive
        if on_archive:
            on_archive(self)
        # trigger post operation signal
        send_post_version_operation(
            constants.OPERATION_ARCHIVE, version=self, token=action_token
        )
        if emit_content_change:
            emit_content_change(self.content)

    @transition(
        field=state,
        source=constants.DRAFT,
        target=constants.ARCHIVED,
        permission=check_archive.as_bool,
    )
    def _set_archive(self, user):
        """State machine transition method for moving version
        from DRAFT to ARCHIVED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass

    check_publish = Conditions(
        [
            user_can_publish(permission_error_message),
            in_state([constants.DRAFT], _("Version is not in draft state")),
        ]
    )

    def can_be_published(self):
        return can_proceed(self._set_publish)

    def publish(self, user, visibility_start=None, visibility_end=None):
        """Change state to PUBLISHED and unpublish currently
        published versions"""
        # trigger pre operation signal
        action_token = send_pre_version_operation(
            constants.OPERATION_PUBLISH, version=self
        )
        self._set_publish(user)
        self.visibility_start = visibility_start
        self.visibility_end = visibility_end
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.PUBLISHED,
            user=user,
        )
        # Only one published version is allowed per unique grouping values.
        # Set all other published versions to unpublished
        pks_for_grouping_values = self.versionable.for_content_grouping_values(
            self.content
        ).values_list("pk", flat=True)
        to_unpublish = Version.objects.exclude(pk=self.pk).filter(
            state=constants.PUBLISHED,
            object_id__in=pks_for_grouping_values,
            content_type=self.content_type,
        )
        for version in to_unpublish:
            version.unpublish(user, to_be_published=self)
        on_publish = self.versionable.on_publish
        if on_publish:
            on_publish(self)
        # trigger post operation signal
        send_post_version_operation(
            constants.OPERATION_PUBLISH,
            version=self,
            token=action_token,
            unpublished=list(to_unpublish),
        )
        if emit_content_change:
            emit_content_change(self.content)

    @transition(
        field=state,
        source=constants.DRAFT,
        target=constants.PUBLISHED,
        permission=check_publish.as_bool,
    )
    def _set_publish(self, user):
        """State machine transition method for moving version
        from DRAFT to PUBLISHED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass

    def is_visible(self):
        now = timezone.now()
        return self.state == constants.PUBLISHED and (
            self.visibility_start is None or self.visibility_start < now
        ) and (
            self.visibility_end is None or self.visibility_end > now
        )

    check_unpublish = Conditions([
        user_can_publish(permission_error_message),
        in_state([constants.PUBLISHED], _("Version is not in published state")),
        draft_is_not_locked(lock_draft_error_message),
    ])

    def can_be_unpublished(self):
        return can_proceed(self._set_unpublish)

    def unpublish(self, user, to_be_published=None):
        """Change state to UNPUBLISHED"""
        # trigger pre operation signal
        action_token = send_pre_version_operation(
            constants.OPERATION_UNPUBLISH, version=self, to_be_published=to_be_published
        )
        self._set_unpublish(user)
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.PUBLISHED,
            new_state=constants.UNPUBLISHED,
            user=user,
        )
        on_unpublish = self.versionable.on_unpublish
        if on_unpublish:
            on_unpublish(self)
        # trigger post operation signal
        send_post_version_operation(
            constants.OPERATION_UNPUBLISH,
            version=self,
            token=action_token,
            to_be_published=to_be_published,
        )
        if emit_content_change:
            emit_content_change(self.content)

    @transition(
        field=state,
        source=constants.PUBLISHED,
        target=constants.UNPUBLISHED,
        permission=check_unpublish.as_bool,
    )
    def _set_unpublish(self, user):
        """State machine transition method for moving version
        from PUBLISHED to UNPUBLISHED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass

    def has_publish_permission(self, user) -> bool:
        """
        Check if the given user has permission to publish.

        Args:
            user (User): The user to check for permission.

        Returns:
            bool: True if the user has publish permission, False otherwise.
        """
        return self._has_permission("publish", user)

    def has_change_permission(self, user) -> bool:
        """
        Check whether the given user has permission to change the object.

        Parameters:
            user (User): The user for which permission needs to be checked.

        Returns:
            bool: True if the user has permission to change the object, False otherwise.
        """
        return self._has_permission("change", user)

    def _has_permission(self, perm: str, user) -> bool:
        """
        Check if the user has the specified permission for the content by
        checking the content's has_publish_permission, has_placeholder_change_permission,
        or has_change_permission methods.

        Falls back to Djangos change permission for the content object.
        """
        if perm == "publish" and hasattr(self.content, "has_publish_permission"):
            # First try explicit publish permission
            return self.content.has_publish_permission(user)
        if hasattr(self.content, "has_change_permission"):
            # First fallback: change permissions
            return self.content.has_change_permission(user)
        if hasattr(self.content, "has_placeholder_change_permission"):
            # Second fallback: placeholder change permissions - works for PageContent
            return self.content.has_placeholder_change_permission(user)
        # final fallback: Django perms
        return user.has_perm(f"{self.content_type.app_label}.change_{self.content_type.model}")

    check_modify = Conditions(
        [
            in_state([constants.DRAFT], not_draft_error),
            draft_is_not_locked(lock_draft_error_message),
            user_can_unlock(permission_error_message),
        ]
    )
    check_revert = Conditions(
        [
            user_can_change(permission_error_message),
            in_state(
                [constants.ARCHIVED, constants.UNPUBLISHED],
                _("Version is not in archived or unpublished state"),
            ),
            draft_is_not_locked(lock_draft_error_message),
        ]
    )
    check_discard = Conditions(
        [
            in_state([constants.DRAFT], not_draft_error),
            is_not_locked(lock_error_message),
        ]
    )
    check_edit_redirect = Conditions(
        [
            in_state(
                [constants.DRAFT, constants.PUBLISHED],
                _("Version is not in draft or published state"),
            ),
            draft_is_not_locked(lock_draft_error_message),
        ]
    )
    check_lock = Conditions(
        [
            in_state([constants.DRAFT], not_draft_error),
            is_not_locked(_("Version is already locked"))
        ]
    )
    check_unlock = Conditions(
        [
            in_state([constants.DRAFT, constants.PUBLISHED], not_draft_error),
            draft_is_locked(_("Draft version is not locked"))

        ]
    )


class StateTracking(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    old_state = models.CharField(max_length=100, choices=constants.VERSION_STATES)
    new_state = models.CharField(max_length=100, choices=constants.VERSION_STATES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
