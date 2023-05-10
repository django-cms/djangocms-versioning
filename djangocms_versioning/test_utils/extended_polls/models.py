from cms.extensions import PageContentExtension
from cms.extensions.extension_pool import extension_pool
from django.db import models


class PollPageContentExtension(PageContentExtension):
    votes = models.IntegerField()


extension_pool.register(PollPageContentExtension)
