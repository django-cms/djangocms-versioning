from cms.models import CMSPlugin
from django.db import models


class Text(CMSPlugin):
    body = models.TextField()

    def __str__(self):
        return self.body or str(self.pk)
