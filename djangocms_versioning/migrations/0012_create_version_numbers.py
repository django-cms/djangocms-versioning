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

    """
    Look at how the grouper admin selector gets the list
    from that list you should then be able to query the versions by filter_by_grouping_fields
    
    # Get all objects for grouper
    all_versions_for_grouper = versionable.for_grouper(versionable.grouper_field)

    # For each possible combination of grouping values


    grouping_values = versionable.grouping_values(self.content)

    fields = list(versionable.grouping_fields)

    content_type = ContentType.objects.get_for_model(versionable.content_model)
    content_objects = versionable.for_grouping_values(fields)

    #versionable.grouping_values(versionable.version_model_proxy.content)

    version_list = Version.objects.filter_by_grouping_fields(
        versionable, **versionable.grouping_fields
    ).all()
    
    """

    # For each registered version model
    for versionable in versioning_extension.versionables:

        distinct_groupers = versionable.distinct_groupers().all()

        # For each grouper
        # FIXME: No good as it doesn't provide pages with different languages!!
        for grouper_content in distinct_groupers:

            fields = versionable.grouping_values(grouper_content)

            content_objects = versionable.for_grouping_values(**fields)
            content_type = ContentType.objects.get_for_model(versionable.content_model)

            version_list = Version.objects.filter(
                object_id__in=content_objects,
                content_type=content_type,
            )


            """
            version_list = Version.objects.filter_by_grouping_fields(
                versionable, **fields
            ).all()
            
  
            grouper_field = versionable.grouper_model
            content_for_grouper = versionable.for_grouper(grouper_field)

            # Get the content for each grouper using the grouping fields
            unique_grouper = versionable.for_content_grouping_values(grouper_content).order_by('pk')

            number = 0
            for version in content_versions:
                number = number + 1
                version_number = version.number
                version.number = number
                continue
            """
            continue

    raise Exception('Migration prevented for dev')

class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_versioning', '0011_version_number'),
    ]

    operations = [
        migrations.RunPython(forwards)
    ]
