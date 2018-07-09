import copy

from django.db import models
from djangocms_versioning.models import BaseVersion


class Poll(models.Model):
    name = models.TextField()

    def __str__(self):
        return "{} ({})".format(self.name, self.pk)


class PollContent(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.text


class Answer(models.Model):
    poll_content = models.ForeignKey(PollContent, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class PollVersion(BaseVersion):
    # Must be specified for Version to be able to filter by that field
    grouper_field = 'content__poll'

    content = models.OneToOneField(PollContent, on_delete=models.CASCADE)

    def __str__(self):
        import pdb; pdb.set_trace()
        return "content_id={} (id={})".format(self.content_id, self.pk)

    def copy_content(self, new):
        content = copy.deepcopy(self.content)
        content.pk = None
        content.save()
        [
            Answer.objects.create(
                text=answer.text,
                poll_content=content,
            ) for answer in self.content.answer_set.all()
        ]
        return content


class VersionWithoutGrouperField(BaseVersion):
    pass
