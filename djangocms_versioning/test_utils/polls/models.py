from cms.models import CMSPlugin
from django.db import models
from django.urls import reverse


class Poll(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class PollContent(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:polls_pollcontent_changelist")

    def get_preview_url(self):
        return reverse("admin:polls_pollcontent_preview", args=[self.id])


class Answer(models.Model):
    poll_content = models.ForeignKey(PollContent, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class PollPlugin(CMSPlugin):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.poll)
