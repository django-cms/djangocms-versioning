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

    # Specifies copy/duplication order
    # Content must be duplicated first, so new Answer objects can point
    # to the new Content object
    copy_field_order = ('content', 'answers')

    content = models.OneToOneField(PollContent, on_delete=models.CASCADE)
    answers = models.ManyToManyField(Answer)

    def copy_answers(self, new):
        """self - current Version
        new - new Version

        New Version's content field already points to a new Content,
        so it can be used to create new Answer objects.
        """
        return [
            Answer.objects.create(
                text=answer.text,
                poll_content=new.content,
            ) for answer in self.answers.all()
        ]
