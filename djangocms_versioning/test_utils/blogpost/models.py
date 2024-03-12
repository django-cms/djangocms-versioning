from django.db import models
from django.urls import reverse


class BlogPost(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class BlogContent(models.Model):
    blogpost = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def has_publish_permission(self, user):
        if user.is_superuser:
            return True
        # Fake a simple object-dependent permission
        return user.username in self.text

    def has_change_permission(self, user):
        if user.is_superuser:
            return True
        # Fake a simple object-dependent permission
        return f"<{user.username}>" in self.text

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:blogpost_blogcontent_changelist")


class Comment(models.Model):
    blogpost = models.ForeignKey(BlogPost, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.pk)


class CommentContent(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:blogpost_commentcontent_changelist")
