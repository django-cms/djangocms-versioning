from __future__ import unicode_literals

from django.db import connection, migrations


def forwards(apps, schema_editor):

    # Or alternatively
    PageContent = apps.get_model("cms", "PageContent")
    old_unique_together = PageContent._meta.unique_together
    new_unique_together = old_unique_together - {("language", "page")}
    if connection.settings_dict["ENGINE"].rsplit(".")[-1] == "mysql":
        in_atomic_block = schema_editor.connection.in_atomic_block
        schema_editor.connection.in_atomic_block = False
        try:
            schema_editor.alter_unique_together(
                PageContent, old_unique_together, new_unique_together
            )
        finally:
            schema_editor.connection.in_atomic_block = in_atomic_block
    else:
        schema_editor.alter_unique_together(
            PageContent, old_unique_together, new_unique_together
        )


def backwards(apps, schema_editor):
    PageContent = apps.get_model("cms", "PageContent")
    old_unique_together = PageContent._meta.unique_together
    new_unique_together = old_unique_together | {("language", "page")}
    if connection.settings_dict["ENGINE"].rsplit(".")[-1] == "mysql":
        in_atomic_block = schema_editor.connection.in_atomic_block
        schema_editor.connection.in_atomic_block = False
        try:
            schema_editor.alter_unique_together(
                PageContent, old_unique_together, new_unique_together
            )
        finally:
            schema_editor.connection.in_atomic_block = in_atomic_block
    else:
        schema_editor.alter_unique_together(
            PageContent, old_unique_together, new_unique_together
        )


class Migration(migrations.Migration):

    dependencies = [
        ("djangocms_versioning", "0008_auto_20180820_1754"),
        ("cms", "0032_remove_title_to_pagecontent"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
