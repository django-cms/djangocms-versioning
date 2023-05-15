# Generated by Django 3.2.19 on 2023-05-05 09:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djangocms_versioning', '0015_version_modified'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='version',
            options={'permissions': (('delete_versionlock', 'Can unlock verision'),)},
        ),
        migrations.AddField(
            model_name='version',
            name='locked_by',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='locking_users', to=settings.AUTH_USER_MODEL, verbose_name='locked by'),
        ),
    ]
