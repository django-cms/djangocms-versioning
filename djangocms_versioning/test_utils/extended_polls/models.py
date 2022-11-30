from django.db import models

from cms.extensions import PageContentExtension
from cms.extensions.extension_pool import extension_pool


class PollPageContentExtension(PageContentExtension):
    votes = models.IntegerField()


extension_pool.register(PollPageContentExtension)
