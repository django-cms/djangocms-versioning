from django.db import models


class Person(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class PersonContent(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return "/"
