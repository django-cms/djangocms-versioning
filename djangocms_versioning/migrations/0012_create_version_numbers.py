from django.apps import apps
from django.db import migrations
from django.db.models import Max


def _distinct_groupers(versionable):
    inner = (
        versionable.content_model._base_manager.values(*versionable.grouping_fields)
        .annotate(Max("pk"))
        .values("pk__max")
    )
    return versionable.content_model._base_manager.filter(id__in=inner).all()


def forwards(app_registry, schema_editor):
    """
    Assign version numbers to existing data

    Removed because versions will always be created after this point, and it is causing dependency problems with other packages tests.
    Anyone that requires this migration can install version 0.0.23, which is the last version with it enabled.
    """
    return
    # versioning_extension = apps.get_app_config("djangocms_versioning").cms_extension
    # Version = app_registry.get_model("djangocms_versioning", "Version")
    # ContentType = apps.get_model("contenttypes", "ContentType")

    # # For each registered version model
    # for versionable in versioning_extension.versionables:
    #     # For each distinct grouper, unique to the grouping field values
    #     for content in _distinct_groupers(versionable):

    #         fields = versionable.grouping_values(content)
    #         content_objects = versionable.for_grouping_values(**fields)
    #         content_type = ContentType.objects.get_for_model(versionable.content_model)

    #         version_list = Version.objects.filter(
    #             object_id__in=content_objects, content_type_id=content_type.pk
    #         ).order_by("pk")

    #         previous_number = 0
    #         for version in version_list:
    #             version.number = previous_number + 1
    #             previous_number = version.number
    #             version.save()


class Migration(migrations.Migration):

    dependencies = [("djangocms_versioning", "0011_version_number")]

    operations = [migrations.RunPython(forwards)]
