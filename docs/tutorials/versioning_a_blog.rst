Tutorial: version your own models
=================================

django CMS pages, aliases and stories are versioned for you the moment you install
djangocms-versioning (see :doc:`/index`). This tutorial is about the *other* case:
you have your own model and you want drafts, publishing and history for it too.

We will take a tiny blog app with a single ``Post`` model and turn it into a fully
versioned one. By the end you will have created a draft, published it, edited it into
a new draft, and published again — watching the version states change at every step.

It takes about 15 minutes and assumes:

- a running django CMS 4 project with djangocms-versioning installed,
- a superuser to log in with, and
- the blog app below.

Here is our starting point — one model, no versioning:

.. code-block:: python

    # blog/models.py
    from django.db import models


    class Post(models.Model):
        author = models.CharField(max_length=80)
        title = models.CharField(max_length=120)
        body = models.TextField()

        def __str__(self):
            return self.title


Step 1 — Split the model into a grouper and a content model
-----------------------------------------------------------

Versioning needs two models instead of one:

- a **grouper** that represents *the post* and never changes between versions, and
- a **content** model that holds everything that *does* change from version to version.

Move the versioned fields (``title``, ``body``) onto a new ``PostContent`` model and
point it back at ``Post`` with a foreign key. ``author`` stays on ``Post`` — the
person who owns the post is the same no matter which version you are looking at:

.. code-block:: python

    # blog/models.py
    from django.db import models


    class Post(models.Model):
        """The grouper: one row per blog post. Holds non-versioned data."""

        author = models.CharField(max_length=80)

        def __str__(self):
            return f"Post by {self.author} ({self.pk})"


    class PostContent(models.Model):
        """The content: one row per *version* of a post."""

        post = models.ForeignKey(Post, on_delete=models.CASCADE)
        title = models.CharField(max_length=120)
        body = models.TextField()

        def __str__(self):
            return self.title

``Post`` is now what gets versioned; each ``PostContent`` is one version of it. The
names are up to you — ``Post``/``PostContent`` is just the common convention.

.. tip::

    Decide field-by-field: does this value need its own history? Put it on
    ``PostContent`` (here, ``title`` and ``body``). Should it stay the same across
    every version (e.g. the ``author``, an owning site)? Leave it on ``Post``.


Step 2 — Tell versioning about the models
-----------------------------------------

Add a ``cms_config.py`` to the app. This is where django CMS apps declare how they
plug into the CMS and its ecosystem.

Instead of importing ``VersionableItem`` from djangocms-versioning directly, ask
django CMS for it through the **versioning contract**. ``get_contract`` returns the
registered ``VersionableItem`` class, so your app depends only on django CMS — not on
a specific versioning package. This is how the ecosystem apps (aliases, stories,
snippets) integrate too:

.. code-block:: python

    # blog/cms_config.py
    from cms.app_base import CMSAppConfig

    from .models import PostContent


    class BlogCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True

        def __init__(self, app):
            super().__init__(app)
            VersionableItem = self.get_contract("djangocms_versioning")
            self.versioning = [
                VersionableItem(
                    content_model=PostContent,
                    grouper_field_name="post",
                    grouper_admin_mixin="__default__",
                ),
            ]

What's happening here:

- ``djangocms_versioning_enabled = True`` opts the app into versioning.
- ``self.get_contract("djangocms_versioning")`` fetches the ``VersionableItem`` class
  through the contract, keeping your code decoupled from the versioning implementation.
  (If you avoid importing directly, your app will also work with altenative implementations
  honoring the contract).
- ``VersionableItem`` connects the content model (``PostContent``) to its grouper via
  the ``post`` foreign key.
- ``grouper_admin_mixin="__default__"`` adds the versioning columns and actions to the
  ``Post`` admin automatically (Step 3).

We don't pass a ``copy_function``: when it is omitted, versioning falls back to its
built-in ``default_copy``, which is all a simple model needs. See
:doc:`/introduction/versioning_integration` for when (and how) to supply a custom one.


Step 3 — Show versions in the admin
-----------------------------------

Register the **grouper** model. Because we set ``grouper_admin_mixin="__default__"``,
the grouper admin gets the author, modified date, state indicator and version actions
added for you.

You also register a small, **hidden** admin for the content model. You never use it
directly, but versioning's version-list view needs to reverse the content model's admin
URLs — without it, opening the version list raises ``NoReverseMatch``. We hide it from
the admin index and redirect it to the grouper admin:

.. code-block:: python

    # blog/admin.py
    from cms.admin.utils import GrouperModelAdmin
    from django.contrib import admin
    from django.shortcuts import redirect

    from .models import Post, PostContent


    @admin.register(Post)
    class PostAdmin(GrouperModelAdmin):
        # "author" lives on the grouper; versioning adds the version author,
        # modified date, state and actions automatically
        list_display = ("content__title", "author")


    @admin.register(PostContent)
    class PostContentAdmin(admin.ModelAdmin):
        """Hidden helper: makes the content model's admin URLs reversible so
        versioning's version list works. Users never see or use it."""

        def has_module_permission(self, request):
            return False  # hide from the admin index

        def changelist_view(self, request, extra_context=None):
            return redirect("admin:blog_post_changelist")

        def change_view(self, request, object_id, form_url="", extra_context=None):
            return redirect("admin:blog_post_changelist")

``GrouperModelAdmin`` (from django CMS 4.1+) recognises ``PostContent`` as the
content model by naming convention, so the grouper admin needs nothing else.

.. note::

    The hidden ``PostContentAdmin`` is a temporary workaround. django CMS 5.1's grouper
    admin resolves these URLs itself, so on 5.1 (or a release that backports it) you can
    drop the content admin and register only the grouper.


Step 4 — Create the database tables
-----------------------------------

.. code-block:: bash

    python -m manage makemigrations blog
    python -m manage migrate

If your blog already had data in the old single-model table, see the data-migration
note in :doc:`/introduction/versioning_integration` — you need to create a grouper
for each existing row. For a brand-new app there is nothing extra to do.


Step 5 — Draft, publish, edit, publish
--------------------------------------

Now the fun part. Open a shell and follow along — the comments show what to expect:

.. code-block:: bash

    python -m manage shell

.. code-block:: python

    from django.contrib.auth import get_user_model
    from djangocms_versioning.models import Version
    from blog.models import Post, PostContent

    user = get_user_model().objects.first()

    # Create the grouper (with its non-versioned author), then the first
    # version of its content.
    post = Post.objects.create(author="Ada Lovelace")
    content = PostContent.objects.with_user(user).create(
        post=post,
        title="Hello, versioning",
        body="My first versioned post.",
    )

    # Creating content through the versioned manager also created a Version — as a draft.
    version = Version.objects.get_for_content(content)
    version.state                                  # 'draft'

.. note::

    Always use ``.with_user(user).create(...)`` for versioned content: versioning
    needs to know *who* is creating the version. A plain ``.create(...)`` will warn
    and skip creating the ``Version`` object.

Drafts are private. The default manager only ever returns published content, so the
public site cannot see this draft yet:

.. code-block:: python

    PostContent.objects.filter(post=post).count()  # 0 — nothing is published

Publish it:

.. code-block:: python

    version.publish(user)
    version.state                                  # 'published'
    PostContent.objects.get(post=post).title       # 'Hello, versioning'

Now edit it. You never change a published version in place — you copy it into a new
draft, change that, and publish when ready:

.. code-block:: python

    draft = version.copy(user)                     # a fresh draft, copied from the published version
    draft.state                                    # 'draft'
    draft.content.title = "Hello, versioning (revised)"
    draft.content.save()

    # The public still sees the published version while you work on the draft:
    PostContent.objects.get(post=post).title       # 'Hello, versioning'

    draft.publish(user)
    PostContent.objects.get(post=post).title       # 'Hello, versioning (revised)'

Publishing the new draft automatically unpublished the previous version, so the post
now has two versions — one unpublished, one published:

.. code-block:: python

    for v in Version.objects.filter_by_grouper(post).order_by("number"):
        print(v.number, v.state)
    # 1 unpublished
    # 2 published


Step 6 — See it in the admin
----------------------------

Log into ``/admin/``, open **Posts**, and you will see your post with its author,
last-modified date and a state indicator. Use the actions menu to **edit** (create a
new draft), **publish**, **unpublish** or open the **manage versions** view, which
lists every version with its state and lets you revert to an older one.


What you have learned
---------------------

- A versioned model is a **grouper** plus a **content** model.
- ``cms_config.py`` registers the pair with a ``VersionableItem``.
- ``.with_user(user).create(...)`` makes drafts; ``version.publish(user)`` makes them
  public; ``version.copy(user)`` starts the next draft.
- The default ``objects`` manager shows only published content; reach for
  ``admin_manager`` when you need every version (see :doc:`/introduction/working_with_pages`).

Where to next:

- :doc:`/introduction/versioning_integration` — custom copy functions (for posts with
  related objects like comments or polls), extra grouping fields such as ``language``,
  and the contract-based ``get_contract`` registration that decouples your app from a
  specific versioning package.
- :doc:`/introduction/basic_concepts` — what the four version states mean and why.
- :doc:`/api/settings` and :doc:`/howto/configuration` — tuning versioning for your project.
