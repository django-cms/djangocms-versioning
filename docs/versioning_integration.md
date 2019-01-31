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
from djangocms_versioning.datastructures import VersionableItem, default_copy
from .models import PostContent


class BlogCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True  # -- 1
    versioning = [
        VersionableItem(   # -- 2
            content_model=PostContent,
            grouper_field_name='post',
            copy_function=default_copy,
            preview_url=<FUNCTION_NAME>
        ),
    ]
```

1. This must be set to True for Versioning to read app's CMS config.
2. `versioning` attribute takes a list of `VersionableItem` objects.

    `VersionableItem` has the following attributes:

    - content_model - *content model* class - in our example it's `PostContent`
    - grouper_field_name - name of the field on the content model which is
    a relation to *grouper model* - in the example it's `post`
    - copy_function - a function that copies a content instance. This is
    used for some operations in versioning such as creating new drafts
    from published versions. See the copy function section of this doc for more info.
    - preview_url - This is optional attribute can be pass to override preview url for an object in version list
    table. If it is not passed then if model is a editable, it will render object preview url else
    changelist url.


## The copy function
When configuring versioning we require you to provide a copy function.
We provide a default function for this (djangocms_versioning.datastructures.default_copy),
but there are many cases in which you may need to implement your own, these are:

    - If your content model contains any one2one or m2m fields.
    - If your content model contains a foreign key that relates to an
    object that should be considered part of the version. For example
    if you're versioning a poll object, you might consider the answers
    in the poll as part of a version. If so, you will need to copy
    the answer objects, not just the poll object. On the other hand if
    a poll has an fk to a category model, you probably wouldn't consider
    category as part of the version. In this case the default copy function
    will take care of this.
    - If other models have reverse relationships to your content model.
    - If your content model contains a generic foreign key.


# Overriding how versioning handles core cms models
By default versioning assumes that the VERSIONING_CMS_MODELS_ENABLED setting
is set to True. If you set this to False it will not register any models
from django-cms for versioning. If you set this to False you are free to
register these models again yourself with different options.
See djangocms_versioning.cms_config.VersioningCMSConfig for reference.
