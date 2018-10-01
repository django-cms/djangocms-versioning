from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, can_proceed, transition

from . import constants


try:
    from djangocms_internalsearch.helpers import emit_content_change
except ImportError:
    emit_content_change = None


class VersionQuerySet(models.QuerySet):

    def get_for_content(self, content_object):
        """Returns Version object corresponding to provided content object
        """
        content_type = ContentType.objects.get_for_model(content_object)
        return self.get(
            object_id=content_object.pk,
            content_type=content_type,
        )

    def filter_by_grouper(self, grouper_object):
        """Returns a list of Version objects for the provided grouper
        object
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_grouper[
            grouper_object.__class__
        ]
        content_objects = versionable.for_grouper(grouper_object)
        content_type = ContentType.objects.get_for_model(
            versionable.content_model)
        return self.filter(
            object_id__in=content_objects, content_type=content_type)


class Version(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_('author')
    )
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
    objects = VersionQuerySet.as_manager()

    @property
    def number(self):
        return self.pk

    class Meta:
        unique_together = ("content_type", "object_id")

    def save(self, **kwargs):
        super().save(**kwargs)
        # Only one draft version is allowed per grouper. Set all other
        # drafts to archived
        if self.state == constants.DRAFT:
            pks_for_grouper = self.versionable.for_grouper(
                self.grouper).values_list('pk', flat=True)
            to_archive = Version.objects.exclude(pk=self.pk).filter(
                state=constants.DRAFT, object_id__in=pks_for_grouper,
                content_type=self.content_type)
            for version in to_archive:
                version.archive(self.created_by)
            on_draft_create = self.versionable.on_draft_create
            if on_draft_create:
                on_draft_create(self)
            if emit_content_change:
                emit_content_change(self)

    @property
    def versionable(self):
        """Helper property to get the versionable for the content type
        of the version
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        return versioning_extension.versionables_by_content[
            self.content.__class__]

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
        content_model = self.content.__class__
        versioning_ext = apps.get_app_config(
            'djangocms_versioning').cms_extension
        copy_function = versioning_ext.versionables_by_content[
            content_model].copy_function
        new_content = copy_function(self.content)
        new_version = Version.objects.create(
            content=new_content, created_by=created_by)
        return new_version

    def archive(self, user):
        """Change state to ARCHIVED"""
        self._set_archive(user)
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
        if emit_content_change:
            emit_content_change(self)

    @transition(field=state, source=constants.DRAFT, target=constants.ARCHIVED)
    def _set_archive(self, user):
        """State machine transition method for moving version
        from DRAFT to ARCHIVED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass

    def can_be_published(self):
        return can_proceed(self._set_publish)

    def publish(self, user):
        """Change state to PUBLISHED and unpublish currently
        published versions"""
        self._set_publish(user)
        self.save()
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.PUBLISHED,
            user=user
        )
        # Only one published version is allowed per grouper. Set all other
        # published versions to unpublished
        pks_for_grouper = self.versionable.for_grouper(
            self.grouper).values_list('pk', flat=True)
        to_unpublish = Version.objects.exclude(pk=self.pk).filter(
            state=constants.PUBLISHED, object_id__in=pks_for_grouper,
            content_type=self.content_type)
        for version in to_unpublish:
            version.unpublish(user)
        on_publish = self.versionable.on_publish
        if on_publish:
            on_publish(self)
        if emit_content_change:
            emit_content_change(self)

    @transition(field=state, source=constants.DRAFT, target=constants.PUBLISHED)
    def _set_publish(self, user):
        """State machine transition method for moving version
        from DRAFT to PUBLISHED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass

    def unpublish(self, user):
        """Change state to UNPUBLISHED"""
        self._set_unpublish(user)
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
        if emit_content_change:
            emit_content_change(self)

    @transition(field=state, source=constants.PUBLISHED, target=constants.UNPUBLISHED)
    def _set_unpublish(self, user):
        """State machine transition method for moving version
        from PUBLISHED to UNPUBLISHED state.

        Please refrain from modifying data in this method, as
        state change is not guaranteed to be saved (making it
        possible to be left with inconsistent data)"""
        pass


class StateTracking(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    old_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    new_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
