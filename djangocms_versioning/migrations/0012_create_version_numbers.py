# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.db import migrations


def forwards(app_registry, schema_editor):

    """
    Assign version numbers to existing data
    """

    versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
    Version = app_registry.get_model('djangocms_versioning', 'Version')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # For each registered version model
    for versionable in versioning_extension.versionables:

        distinct_groupers = versionable.distinct_groupers().all()

        #groupers = versionable.content_model._base_manager.all()

        # FIXME: No good as it doesn't provide pages with different languages!!
        # TODO: Requries a query that fetches all groupers with all grouping fields applied
        for content in distinct_groupers:

            fields = versionable.grouping_values(content)
            content_objects = versionable.for_grouping_values(**fields)
            content_type = ContentType.objects.get_for_model(versionable.content_model)

            version_list = Version.objects.filter(
                object_id__in=content_objects,
                content_type_id=content_type.pk,
            ).order_by('pk')

            previous_number = 0
            for version in version_list:
                version.number = previous_number + 1
                previous_number = version.number
                version.save()
                continue

    raise Exception('Migration prevented for dev')

class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_versioning', '0011_version_number'),
    ]

    operations = [
        migrations.RunPython(forwards)
    ]
