from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django_fsm import FSMField, transition

from . import constants


class Version(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey('content_type', 'object_id')
    state = FSMField(
        default=constants.DRAFT, choices=constants.VERSION_STATES, protected=True)

    def save(self, **kwargs):
        super().save(**kwargs)
        # Only one draft version is allowed per grouper. Set all other
        # drafts to archived
        if self.state == constants.DRAFT:
            pks_for_grouper = self.versionable.for_grouper(
                self.grouper).values_list('pk', flat=True)
            to_archive = Version.objects.exclude(pk=self.pk).filter(
                state=constants.DRAFT, object_id__in=pks_for_grouper)
            for version in to_archive:
                version.archive(self.created_by)
                version.save()

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
        """Creates new Version object, with metadata copied over
        from self.

        Introspects relations and duplicates objects that
        Version has a relation to. Default behaviour for duplication is
        implemented in `_copy_function_factory`. This can be overriden
        per-field by implementing `copy_{field_name}` method.
        """
        content_model = self.content.__class__
        content_fields = {
            field.name: getattr(self.content, field.name)
            for field in content_model._meta.fields
            # don't copy primary key because we're creating a new obj
            if content_model._meta.pk.name != field.name
        }
        new_content = content_model.objects.create(**content_fields)
        new_version = Version.objects.create(
            content=new_content, created_by=created_by)
        return new_version

    @transition(field=state, source=constants.DRAFT, target=constants.ARCHIVED)
    def archive(self, user):
        """Change state to ARCHIVED"""
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.ARCHIVED,
            user=user
        )

    @transition(field=state, source=constants.DRAFT, target=constants.PUBLISHED)
    def publish(self, user):
        """Change state to PUBLISHED"""
        StateTracking.objects.create(
            version=self,
            old_state=constants.DRAFT,
            new_state=constants.PUBLISHED,
            user=user
        )

    @transition(field=state, source=constants.PUBLISHED, target=constants.UNPUBLISHED)
    def unpublish(self, user):
        """Change state to UNPUBLISHED"""
        StateTracking.objects.create(
            version=self,
            old_state=constants.PUBLISHED,
            new_state=constants.UNPUBLISHED,
            user=user
        )


class StateTracking(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    old_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    new_state = models.CharField(
        max_length=100, choices=constants.VERSION_STATES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
