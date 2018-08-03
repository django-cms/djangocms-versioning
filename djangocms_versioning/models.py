from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from django_fsm import FSMField, transition

from . import constants


class Version(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )
    object_id = models.PositiveIntegerField()
    content = GenericForeignKey('content_type', 'object_id')
    state = FSMField(
        default=constants.DRAFT, choices=constants.VERSION_STATES, protected=True)

    def copy(self):
        """Creates new Version object, with metadata copied over
        from self.

        Introspects relations and duplicates objects that
        Version has a relation to. Default behaviour for duplication is
        implemented in `_copy_function_factory`. This can be overriden
        per-field by implementing `copy_{field_name}` method.
        """
        content_class = self.content.__class__
        content_fields = {
            field.name: getattr(self.content, field.name)
            for field in content_class._meta.fields
            # don't copy primary key because we're creating a new obj
            if content_class._meta.pk.name != field.name
        }
        new_content = content_class.objects.create(**content_fields)
        new_version = Version.objects.create(content=new_content)
        return new_version

    @transition(field=state, source=constants.DRAFT, target=constants.ARCHIVED)
    def archive(self):
        """Change state to ARCHIVED"""

    @transition(field=state, source=constants.DRAFT, target=constants.PUBLISHED)
    def publish(self):
        """Change state to PUBLISHED"""

    @transition(field=state, source=constants.PUBLISHED, target=constants.UNPUBLISHED)
    def unpublish(self):
        """Change state to UNPUBLISHED"""
