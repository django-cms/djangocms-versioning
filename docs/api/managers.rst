Manager API Reference
=====================

Content Model Managers
----------------------

When a model is registered for versioning, it gets two managers:

1. **objects** (PublishedContentManager): Default manager, only shows published content
2. **admin_manager** (AdminManager): Shows all versions, used in admin interfaces


PublishedContentManager (objects)
---------------------------------

The default manager for versioned content models. It automatically filters to show only published versions.

**Usage**:

.. code-block:: python

    from blog.models import PostContent

    # Get all published posts
    published_posts = PostContent.objects.all()

    # Filter published posts by language
    english_posts = PostContent.objects.filter(language='en')

    # This will only return published versions
    post = PostContent.objects.get(pk=1)


Methods
+++++++

.. py:method:: with_user(user)

    **Parameters**:
        - ``user``: A User instance

    **Returns**: Manager with user context set

    Required when creating new versioned content. Provides the user context needed to create the associated Version object.

    **Example**::

        user = User.objects.first()
        # Create a new draft version (Version object created automatically)
        post = PostContent.objects.with_user(user).create(
            title="My Post",
            text="Content here"
        )

    **Important**: Without calling ``with_user()``, a Version object won't be created and you'll get a warning.

    **Exception Handling**::

        # This will raise ValueError if user is not a User instance
        try:
            PostContent.objects.with_user("invalid").create(...)
        except ValueError as e:
            print(e)  # "with_user requires a User instance"


.. warning::

    Always use ``with_user()`` when creating versioned content outside of the admin interface.
    If you forget, versioning will warn but the object will be created without a version.


AdminManager (admin_manager)
----------------------------

The admin manager provides access to all versions of content, regardless of publication state.
**This should only be used in admin interfaces and admin-only code paths.**

**Usage**:

.. code-block:: python

    from blog.models import PostContent
    from djangocms_versioning.constants import DRAFT, PUBLISHED

    # Get all versions of all posts
    all_posts = PostContent.admin_manager.all()

    # Get all draft versions
    drafts = PostContent.admin_manager.filter(versions__state=DRAFT)

    # Get all published versions
    published = PostContent.admin_manager.filter(versions__state=PUBLISHED)

    # Combine with other filters
    english_drafts = PostContent.admin_manager.filter(
        language='en',
        versions__state=DRAFT
    )


AdminManager Methods
++++++++++++++++++++

.. py:method:: current_content(**kwargs)

    **Parameters**:
        - ``**kwargs``: Optional filter arguments (e.g., language='en')

    **Returns**: QuerySet of current content versions

    Returns the current version of content, defined as:
    1. Draft version if it exists
    2. Published version if no draft exists
    3. Never returns unpublished or archived versions without a draft

    This is useful for admin interfaces where you want to show what the user is currently working on.

    **Example**::

        # Get the current version of all posts
        current_posts = PostContent.admin_manager.current_content()

        # Get current English posts
        current_en = PostContent.admin_manager.current_content(language='en')

        # Use in an admin queryset
        class PostAdmin(admin.ModelAdmin):
            def get_queryset(self, request):
                return PostContent.admin_manager.current_content()


.. py:method:: latest_content(**kwargs)

    **Parameters**:
        - ``**kwargs``: Optional filter arguments (e.g., language='en')

    **Returns**: QuerySet of latest content versions

    Returns the latest version of content in this order:
    1. Draft version (if exists)
    2. Published version (if no draft)
    3. Any other version with the highest pk

    This is useful when you want to show the newest version regardless of its state.

    **Example**::

        # Get the latest version of all posts
        latest_posts = PostContent.admin_manager.latest_content()

        # Get latest versions that are in a specific category
        latest_in_category = PostContent.admin_manager.latest_content(
            category=some_category
        )


Manager Mixins (for Custom Managers)
------------------------------------

If you define a custom manager on your content model, use these mixins:

.. py:class:: PublishedContentManagerMixin

    Mixin that provides the versioning behavior for the ``objects`` manager.

    **Example**::

        from django.db import models
        from djangocms_versioning.managers import PublishedContentManagerMixin

        class PostContent(models.Model):
            title = models.CharField(max_length=200)
            text = models.TextField()

            objects = models.Manager.from_queryset(PublishedContentManagerMixin)()


.. py:class:: AdminManagerMixin

    Mixin that provides the versioning behavior for the ``admin_manager``.

    **Example**::

        from django.db import models
        from djangocms_versioning.managers import AdminManagerMixin

        class PostContent(models.Model):
            title = models.CharField(max_length=200)
            text = models.TextField()

            admin_manager = models.Manager.from_queryset(AdminManagerMixin)()


Common Manager Patterns
-----------------------

Creating Versioned Content
++++++++++++++++++++++++++++

.. code-block:: python

    from django.contrib.auth import get_user_model
    from blog.models import PostContent

    User = get_user_model()
    user = User.objects.first()

    # Correct: with_user() creates a Version object
    post = PostContent.objects.with_user(user).create(
        title="My Post",
        text="Content"
    )

    # Incorrect: No Version object will be created
    post = PostContent.objects.create(
        title="My Post",
        text="Content"
    )  # Warning: "No user has been supplied..."


Filtering by State
+++++++++++++++++++

.. code-block:: python

    from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED, ARCHIVED

    # Draft versions
    drafts = PostContent.admin_manager.filter(versions__state=DRAFT)

    # Published versions
    published = PostContent.admin_manager.filter(versions__state=PUBLISHED)

    # Non-published versions
    unpublished = PostContent.admin_manager.exclude(versions__state=PUBLISHED)

    # Multiple states
    active = PostContent.admin_manager.filter(
        versions__state__in=[DRAFT, PUBLISHED]
    )


Getting Version Information
++++++++++++++++++++++++++++

.. code-block:: python

    from djangocms_versioning.models import Version

    post = PostContent.admin_manager.first()

    # Get the version object for this content
    version = Version.objects.get_for_content(post)

    # Access version metadata
    print(f"State: {version.state}")
    print(f"Author: {version.created_by}")
    print(f"Created: {version.created}")
    print(f"Number: {version.number}")


.. important::

    **Do not use admin_manager on the public website!** It bypasses the security that ensures
    only published versions are visible to visitors. Always use the default ``objects`` manager
    for public-facing queries.
