from django.contrib import admin

from djangocms_versioning.test_utils.blogpost import models


admin.site.register(models.BlogPost)
admin.site.register(models.BlogContent)
