Versioning is an optional feature, so core CMS and 3rd-party apps
should be still usable when versioning is not enabled.

# Integrating Versioning

Let's use an example. There's an existing `blog` application
that has a single model called `Post`:

```python
# polls/models.py
class Post(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
```

Versioning works by creating multiple objects (called **content objects**).
To know what these objects are versions of, there's a contept of **grouper objects**,
which tie select content objects together.

In order to make `blog` app work with versioning, changes to model structure are needed.

```python
# polls/models.py
class Post(models.Model):
    pass


class PostContent(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    text = models.TextField()
```

This structure is not only compatible with versioning,
but also works when versioning is not enabled.

`Post` becomes a **grouper** model and `PostContent` becomes a **content** model.

Versioning needs to be aware of these models. This can be done in `cms_config.py` file:

```python
# polls/cms_config.py
class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True  # -- 1
    versioning = [
        VersionableItem(   # -- 2
            content_model=PollContent,
            grouper_field_name='poll',
        ),
    ]
```

1. This line instructs CMS to pass this configuration to Versioning
2. `versioning` attribute takes a list of `VersionableItem` objects.

    `VersionableItem` has the following attributes:

    - content_model - *content model* class - in our example it's `PollContent`
    - grouper_field_name - name of the field on the content model which is
    a relation to *grouper model* - in the example it's `poll`
