from django.db import models


class IncorrectBlogPost(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class IncorrectBlogContent(models.Model):
    blogpost = models.ForeignKey(IncorrectBlogPost, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text
