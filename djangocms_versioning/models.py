from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, can_proceed, transition

from . import constants, versionables
from .conditions import Conditions, in_state


try:
    from djangocms_internalsearch.helpers import emit_content_change
except ImportError:
    emit_content_change = None


class VersionQuerySet(models.QuerySet):

    def get_for_content(self, content_object):
        """Returns Version object corresponding to provided content object
        """
        if hasattr(content_object, '_version_cache'):
            return content_object._version_cache
        versionable = versionables.for_content(content_object)
        version = self.get(
            object_id=content_object.pk,
            content_type__in=versionable.content_types,
        )
        content_object._version_cache = version
        return version

    def filter_by_grouper(self, grouper_object):
        """Returns a list of Version objects for the provided grouper
        object
        """
        versionable = versionables.for_grouper(grouper_object)
        return self.filter_by_grouping_values(versionable, **{
            versionable.grouper_field_name: grouper_object,
        })

    def filter_by_grouping_values(self, versionable, **kwargs):
        """Returns a list of Version objects for the provided grouping
        values (unique grouper version list)
        """
        content_objects = versionable.for_grouping_values(**kwargs)
        return self.filter(
            object_id__in=content_objects,
            content_type__in=versionable.content_types,
        )

    def filter_by_content_grouping_values(self, content):
        """Returns a list of Version objects for grouping values taken
       from provided content object. In other words:
       it uses the content instance property values as filter parameters
        """
        versionable = versionables.for_content(content)
        content_objects = versionable.for_content_grouping_values(content)
        return self.filter(
            object_id__in=content_objects,
            content_type__in=versionable.content_types,
        )


class Version(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_('author')
    )
    number = models.CharField(max_length=11)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey('content_type', 'object_id')
    state = FSMField(
        default=constants.DRAFT,
        choices=constants.VERSION_STATES,
        verbose_name=_('status'),
        protected=True,
    )
    source = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('source'),
    )
    objects = VersionQuerySet.as_manager()

    class Meta:
        unique_together = ("content_type", "object_id")

    def __str__(self):
        return "Version #{}".format(self.pk)

    def save(self, **kwargs):
        from .operations import send_post_version_operation, send_pre_version_operation

        created = not self.pk
        # On version creation
        if created:
            # trigger pre operation signal
            action_token = send_pre_version_operation(constants.DRAFT, obj=self)
            # Set the version number
            self.number = self.make_version_number()

        super().save(**kwargs)
        # Only one draft version is allowed per unique grouping values.
        # Set all other drafts to archived
        if self.state == constants.DRAFT:
            if created:
                pks_for_grouping_values = self.versionable.for_content_grouping_values(
                    self.content).values_list('pk', flat=True)
                to_archive = Version.objects.exclude(pk=self.pk).filter(
                    state=constants.DRAFT, object_id__in=pks_for_grouping_values,
                    content_type=self.content_type)
                for version in to_archive:
                    version.archive(self.created_by)
                on_draft_create = self.versionable.on_draft_create
                if on_draft_create:
                    on_draft_create(self)
                # trigger post operation signal
                send_post_version_operation(constants.DRAFT, action_token, obj=self)
            if emit_content_change:
                emit_content_change(self.content, created=created)

    def make_version_number(self):
        """
        Create a version number for each version
        """
        # Get the latest version object
        latest_version = Version.objects.filter_by_content_grouping_values(
            self.content
        ).order_by('-pk').first()
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

    @property
    def grouper(self):
        """Helper property to get the grouper for the version
        """
        return getattr(
            self.content, self.versionable.grouper_field_name)

    def copy(self, created_by):
        """Creates a new Version object, with a copy of the related
        content object.
        Allows customization of how the content object will be copied
        when specified in cms_config.py
        """
        copy_function = versionables.for_content(self.content).copy_function
        new_content = copy_function(self.content)
        new_version = Version.objects.create(
            content=new_content,
            source=self,
            created_by=created_by,
        )
        return new_version

    check_archive = Conditions()

    def can_be_archived(self):
        return can_proceed(self._set_archive)

    def archive(self, user):
        from .operations import send_post_version_operation, send_pre_version_operation

        # trigger pre operation signal
        action_token = send_pre_version_operation(constants.ARCHIVED, obj=self)
        """Change state to ARCHIVED"""
        self._set_archive(user)
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.ARCHIVED,
            user=user
        )
        on_archive = self.versionable.on_archive
        if on_archive:
            on_archive(self)
        # trigger post operation signal
        send_post_version_operation(constants.ARCHIVED, action_token, obj=self)
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

    check_publish = Conditions()

    def can_be_published(self):
        return can_proceed(self._set_publish)

    def publish(self, user):
        """Change state to PUBLISHED and unpublish currently
        published versions"""
        from .operations import send_post_version_operation, send_pre_version_operation

        # trigger pre operation signal
        action_token = send_pre_version_operation(constants.PUBLISHED, obj=self)
        self._set_publish(user)
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.PUBLISHED,
            user=user
        )
        # Only one published version is allowed per unique grouping values.
        # Set all other published versions to unpublished
        pks_for_grouping_values = self.versionable.for_content_grouping_values(
            self.content).values_list('pk', flat=True)
        to_unpublish = Version.objects.exclude(pk=self.pk).filter(
            state=constants.PUBLISHED, object_id__in=pks_for_grouping_values,
            content_type=self.content_type)
        for version in to_unpublish:
            version.unpublish(user)
        on_publish = self.versionable.on_publish
        if on_publish:
            on_publish(self)
        # trigger post operation signal
        send_post_version_operation(constants.PUBLISHED, action_token, obj=self)
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

    check_unpublish = Conditions()

    def can_be_unpublished(self):
        return can_proceed(self._set_unpublish)

    def unpublish(self, user):
        from .operations import send_post_version_operation, send_pre_version_operation

        # trigger pre operation signal
        action_token = send_pre_version_operation(constants.UNPUBLISHED, obj=self)
        """Change state to UNPUBLISHED"""
        self._set_unpublish(user)
        self.modified = timezone.now()
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.PUBLISHED,
            new_state=constants.UNPUBLISHED,
            user=user
        )
        on_unpublish = self.versionable.on_unpublish
        if on_unpublish:
            on_unpublish(self)
        # trigger post operation signal
        send_post_version_operation(constants.UNPUBLISHED, action_token, obj=self)
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

    check_modify = Conditions([
        in_state([constants.DRAFT], _('Version is not a draft'))
    ])
    check_revert = Conditions([
        in_state(
            [constants.ARCHIVED, constants.UNPUBLISHED],
            _('Version is not in archived or unpublished state')
        ),
    ])
    check_discard = Conditions([
        in_state([constants.DRAFT], _('Version is not a draft'))
    ])
    check_edit_redirect = Conditions([
        in_state(
            [constants.DRAFT, constants.PUBLISHED],
            _('Version is not in draft or published state')
        ),
    ])


class StateTracking(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    old_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    new_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
