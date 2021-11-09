from django.db import models

from cms.extensions import TitleExtension
from cms.extensions.extension_pool import extension_pool


class PollTitleExtension(TitleExtension):
    votes = models.CharField(max_length=255)


extension_pool.register(PollTitleExtension)
