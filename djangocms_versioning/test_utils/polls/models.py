from django.db import models


class Poll(models.Model):
    name = models.TextField()

    def __str__(self):
        return "{} ({})".format(self.name, self.pk)


class PollExtension(models.Model):
    help_text = models.TextField()


class Survey(models.Model):
    name = models.CharField(max_length=100)


class Tag(models.Model):
    name = models.CharField(max_length=100)


class PollContent(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()
    poll_extension = models.OneToOneField(PollExtension, null=True)
    survey = models.ForeignKey(Survey, null=True)
    tags = models.ManyToManyField(Tag, related_name='poll_contents')

    def __str__(self):
        return self.text


class Answer(models.Model):
    poll_content = models.ForeignKey(PollContent, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class Category(models.Model):
    poll_contents = models.ManyToManyField(
        PollContent, related_name='categories')
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class PollArticle(models.Model):
    poll_content = models.OneToOneField(PollContent)
    text = models.TextField()
