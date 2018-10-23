# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-10-23 14:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_versioning', '0013_auto_20181005_1404'),
    ]

    operations = [
        migrations.AddField(
            model_name='version',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='djangocms_versioning.Version', verbose_name='source'),
        ),
    ]
