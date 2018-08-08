Versioning is an optional feature, so core CMS and 3rd-party apps
should be still usable when versioning is not enabled.

# Integrating Versioning

Let's use an example. There's an existing `blog` application
that has a single model called `Post`:

```python
# blog/models.py
from django.db import models


class Post(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
```

Versioning works by creating multiple objects (called **content objects**).
To know what these objects are versions of, there's a concept of **grouper objects**,
which tie select content objects together.

In order to make `blog` app work with versioning, changes to model structure are needed.

```python
# blog/models.py
from django.db import models


class Post(models.Model):
    pass


class PostContent(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    text = models.TextField()
```

This structure is not only compatible with versioning,
but also works when versioning is not enabled.

Note: With versioning disabled **grouper** essentially becomes a one-to-one
relation to **content**, as it will always be created along with
every new **content** object.

`Post` becomes a **grouper** model and `PostContent` becomes a **content** model.

Keep in mind that it's not necessary to rename `Post` to `PostContent`,
it's just a naming convention. It's absolutely possible to keep **content** model
named `Post` and have `PostGrouper` as a name of **grouper** model.

Versioning needs to be aware of these models. This can be done in `cms_config.py` file:

```python
# blog/cms_config.py
from cms.app_base import CMSAppConfig
from djangocms_versioning.datastructures import VersionableItem
from .models import PostContent


class BlogCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True  # -- 1
    versioning = [
        VersionableItem(   # -- 2
            content_model=PostContent,
            grouper_field_name='post',
        ),
    ]
```

1. This must be set to True for Versioning to read app's CMS config.
2. `versioning` attribute takes a list of `VersionableItem` objects.

    `VersionableItem` has the following attributes:

    - content_model - *content model* class - in our example it's `PostContent`
    - grouper_field_name - name of the field on the content model which is
    a relation to *grouper model* - in the example it's `post`
