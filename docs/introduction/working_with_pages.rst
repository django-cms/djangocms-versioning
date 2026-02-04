Working with versioned Pages
=============================

When djangocms-versioning is installed, django CMS pages become versioned. While this
does not change how you interact with ``Page`` and most importantly ``PageContent``
objects in your code, it is important to understand how djangocms-versioning changes the
result of querying ``PageContent`` objects.

Understanding the Page/PageContent relationship
------------------------------------------------

Django CMS separates page structure from page content:

``Page``
    The :term:`grouper model <grouper model>` representing the page in the site tree.
    It holds non-versioned data like the page's position in the navigation hierarchy.

``PageContent``
    The :term:`content model <content model>` holding the versioned content for a
    specific language: title, slug, template, meta description, and placeholders
    with plugins.

A single ``Page`` can have multiple ``PageContent`` objects — one per language, and
potentially multiple versions per language (draft, published, archived, etc.).


Querying PageContent objects
----------------------------

Published content only (default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default ``objects`` manager only returns published content:

.. code-block:: python

    from cms.models import PageContent

    # Get all published English page contents
    PageContent.objects.filter(language="en")

    # Get published content for a specific page
    PageContent.objects.filter(page=my_page, language="en")

    # Get published content for a ``Page`` object
    page.get_content_obj("en")  # caching avoids db hit

This is the safe default for public-facing code —- draft and unpublished content is
never accidentally exposed.


All versions (admin contexts only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``admin_manager`` when you need access to all versions. **Only use this in
admin views, not in public-facing code:**

.. code-block:: python

    from cms.models import PageContent

    # Get all page contents regardless of version state
    PageContent.admin_manager.filter(page=my_page, language="en")


Filtering by version state
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    Since version states are specific to djangocms-versioning, this code ties
    directly to the djangocms-versioning implementation and will not work with other
    versioning solutions.

To find content in a specific state:

.. code-block:: python

    from cms.models import PageContent
    from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED, ARCHIVED

    # Get draft content for a page
    PageContent.admin_manager.filter(
        page=my_page,
        language="en",
        versions__state=DRAFT
    )

    # Get all unpublished versions
    PageContent.admin_manager.filter(versions__state=UNPUBLISHED)


Current content (draft or published)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Often you need the "current" version —- the draft if one exists, otherwise the
published version. Use ``current_content()``:

.. code-block:: python

    from cms.models import PageContent

    # Get current content for all languages of a page
    for content in PageContent.admin_manager.filter(page=my_page).current_content():
        print(f"{content.language}: {content.title}")

    # Get current English content
    current = PageContent.admin_manager.filter(
        page=my_page,
        language="en"
    ).current_content().first()


Working with the Version model
------------------------------

.. note::
    Since the Version model is specific to djangocms-versioning, this code ties
    directly to the djangocms-versioning implementation and will not work with other
    versioning solutions.

Each ``PageContent`` has an associated ``Version`` object that tracks its state:

.. code-block:: python

    from djangocms_versioning.models import Version

    # Get the version for a content object
    version = Version.objects.get_for_content(page_content)
    print(version.state)  # 'draft', 'published', etc.
    print(version.created_by)  # User who created this version
    print(version.modified)  # Last modification timestamp

    # Get all versions for a page/language combination
    versions = Version.objects.filter_by_content_grouping_values(page_content)
    for v in versions.order_by("-pk"):
        print(f"Version {v.number}: {v.state}")



Creating new page content versions
----------------------------------

When creating content programmatically, use ``with_user()`` to track authorship:

.. code-block:: python

    from cms.models import Page, PageContent

    # Create a new page (grouper)
    page = Page.objects.create(node=parent_node)

    # Create versioned content - this also creates a Version object
    content = PageContent.objects.with_user(request.user).create(
        page=page,
        language="en",
        title="My New Page",
        slug="my-new-page",
        template="base.html",
    )

The new content will be in **draft** state. To publish it:

.. code-block:: python

    from djangocms_versioning.models import Version

    version = Version.objects.get_for_content(content)
    version.publish(request.user)


Common patterns
---------------

Check if a page has unpublished changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cms.models import PageContent
    from djangocms_versioning.constants import DRAFT, PUBLISHED

    def has_unpublished_changes(page, language):
        """Returns True if page has a draft that differs from published."""
        contents = PageContent.admin_manager.filter(
            page=page,
            language=language
        ).current_content()
        return contents and contents.versions.first().state == DRAFT


Get the published version of a draft
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    Since the Version model is specific to djangocms-versioning, this code ties
    directly to the djangocms-versioning implementation and will not work with other
    versioning solutions.

.. code-block:: python

    from djangocms_versioning.constants import PUBLISHED
    from djangocms_versioning.models import Version

    def get_published_sibling(draft_content):
        """Given a draft PageContent, find its published counterpart."""
        version = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(draft_content),
            object_id__in=PageContent.admin_manager.filter(
                page=draft_content.page,
                language=draft_content.language
            ).values_list("pk", flat=True),
            state=PUBLISHED
        ).first()
        return version.content if version or None


Iterate over all pages with their current content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Remember using the correct manager when using, e.g. `prefetch_related` or reverse relations

.. code-block:: python

    from django.db.models import Prefetch

    from cms.models import Page, PageContent

    # Unoptimized with N + 1 fetches
    # Manager needs to be specified in the reverse relation
    for page in Page.objects.all():
        for content in page.pagecontent_set(manager="admin_manager").all():
            print(f"{page.pk}: {content.title} ({content.language})")

    # Optimized with 2 fetches
    # Manager needs to be specified in the Prefetch object
    for page in Page.objects.prefetch_related(Prefetch("pagecontent_set", queryset=PageContent.admin_manager.all())).all():
        for content in page.pagecontent_set(manager="admin_manager").all():
            print(f"{page.pk}: {content.title} ({content.language})")
