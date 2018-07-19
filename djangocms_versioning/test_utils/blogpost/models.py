from django.db import models

from djangocms_versioning.models import BaseVersion


class BlogPost(models.Model):
    name = models.TextField()

    def __str__(self):
        return "{} ({})".format(self.name, self.pk)


class BlogContent(models.Model):
    blogpost = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.text


class BlogPostVersion(BaseVersion):
    # Must be specified for Version to be able to filter by that field
    grouper_field = 'content__blogpost'

    content = models.OneToOneField(BlogContent, on_delete=models.CASCADE)

    def __str__(self):
        return "content_id={} (id={})".format(self.content_id, self.pk)


class Comment(models.Model):
    # NOTE: The BlogPost model is technically the grouper for comments
    blogpost = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class CommentVersion(BaseVersion):
    content = models.OneToOneField(Comment, on_delete=models.CASCADE)
