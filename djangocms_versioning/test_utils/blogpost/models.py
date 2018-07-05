import copy

from django.db import models
from djangocms_versioning.models import BaseVersion

class BlogPost(models.Model):
    name = models.TextField()

    def __str__(self):
        return "{} ({})".format(self.name, self.pk)

class BlogContent(models.Model):
    poll = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.text

class Comments(models.Model):
    poll_content = models.ForeignKey(BlogContent, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class BlogPostVersion(BaseVersion):
    # Must be specified for Version to be able to filter by that field
    grouper_field = 'content__blogpost'

    content = models.OneToOneField(BlogContent, on_delete=models.CASCADE)

    def __str__(self):
        return "content_id={} (id={})".format(self.content_id, self.pk)

    # def copy_content(self, new):
    #     content = copy.deepcopy(self.content)
    #     content.pk = None
    #     content.save()
    #     [
    #         Answer.objects.create(
    #             text=answer.text,
    #             poll_content=content,
    #         ) for answer in self.content.answer_set.all()
    #     ]
    #     return content


class VersionWithoutBlogPostGrouperField(BaseVersion):
    pass
