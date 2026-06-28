Welcome to djangocms-versioning documentation!
==============================================

djangocms-versioning adds **drafts, publishing and version history** to django CMS
content. It manages each piece of content through four states — *draft*, *published*,
*unpublished* and *archived* — so editors can work on changes privately and publish
them when ready, while every previous version stays on record.


Installation
------------

You need a django CMS 4.0 (or higher) project already running. Then::

    pip install djangocms-versioning

Add ``djangocms_versioning`` to your project's ``INSTALLED_APPS`` and run::

    python -m manage migrate djangocms_versioning

If you are adding versioning to a project that **already has content**, also run::

    python -m manage create_versions --userid <pk-of-a-user>

to create the ``Version`` objects that mark existing content as published. See
:doc:`/api/management_commands` for details.


It just works with pages, aliases, stories, or snippets
-------------------------------------------------------

For most users that is all the setup there is. Once installed:

- **django CMS pages are versioned automatically** — the page tree shows draft and
  published states, and editing a published page creates a new draft.
- **Ecosystem packages register themselves** through their own ``cms_config.py``, so
  installing
  `djangocms-alias <https://github.com/django-cms/djangocms-alias>`_,
  `djangocms-stories <https://github.com/django-cms/djangocms-stories>`_ or
  `djangocms-snippet <https://github.com/django-cms/djangocms-snippet>`_ alongside
  versioning gives you versioned aliases, stories and snippets with no extra code.

You write code only when you want to version **your own** models — and even then the
work is a small ``cms_config.py`` that registers the model with versioning, exactly as
the ecosystem packages do. That is what the tutorial below walks through. (To stop
django CMS pages being versioned automatically, see ``VERSIONING_CMS_MODELS_ENABLED``
in :doc:`/api/advanced_configuration`.)


.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Tutorial:

   tutorials/versioning_a_blog

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: How-To Guides:

   introduction/versioning_integration
   introduction/working_with_pages
   explanations/admin_options
   explanations/customizing_version_list
   howto/configuration
   howto/permissions
   howto/version_locking
   howto/react_to_version_changes

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Reference:

   api/models
   api/managers
   api/advanced_configuration
   api/signals
   api/management_commands
   api/contract
   api/settings

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Explanation:

   introduction/basic_concepts

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Release notes:

   upgrade/2.6.0
   upgrade/2.5.0
   upgrade/2.4.0
   upgrade/2.0.0


-----


Glossary
--------

.. glossary::

    version model
        A model that stores information such as state (draft, published etc.),
        author, created and modified dates etc. about each version.

    content model
        A model with a one2one relationship with the
        :term:`version model <version model>`, which stores version data specific to
        the content type that is being versioned. It can have relationships
        with other models which could also store version data (for example in the case of
        a poll with many answers, the answers would be kept in a separate
        model, but would also be part of the version).

        See `the grouper / content pattern
        <https://docs.django-cms.org/en/latest/explanation/content_objects.html#the-two-parts>`__
        in the django CMS documentation.

    grouper model
        A model with a one2many relationship with the
        :term:`content model <content model>`. An instance of the grouper
        model groups all the versions of one object. It is in effect the
        object being versioned. It also stores data that is not version-specific.

        See `the grouper / content pattern
        <https://docs.django-cms.org/en/latest/explanation/content_objects.html#the-two-parts>`__
        in the django CMS documentation.

    extra grouping field
        The :term:`content model <content model>` must always have a foreign key
        to the :term:`grouper model <grouper model>`. However, the content model
        can also have additional grouping fields. This is how versioning
        is implemented for the ``cms.PageContent`` model, where ``PageContent.language``
        is defined as an extra grouping field. This supports filtering of objects
        by both its grouper object and its extra grouping fields in the admin and
        in any other implementations (in the page example, this ensures that
        the latest version of a German alias would not be displayed on an English page).

        See `the grouper / content pattern
        <https://docs.django-cms.org/en/latest/explanation/content_objects.html>`__
        in the django CMS documentation.

    copy function
        When creating a new draft version, versioning will usually copy an
        existing version. By default it will copy the current published version,
        but when reverting to an old version, a specific unpublished or archived version
        will be used. A customizable copy function is used for this.

    cms_config
        The ``cms_config.py`` file in a Django app that defines how the app
        integrates with django CMS and djangocms-versioning. It contains a
        ``CMSAppConfig`` subclass with versioning settings.

        See `how to share capabilities between apps
        <https://docs.django-cms.org/en/latest/how_to/20-cms-config.html>`__ in the
        django CMS documentation.

    ExtendedVersionAdminMixin
        A mixin class for Django admin that adds versioning-related fields and
        actions to the admin interface, including author, modified date,
        versioning state, and version management actions.

    extended_admin_field_modifiers
        A configuration option in :term:`cms_config` that allows customizing
        how fields are displayed in admin views that use the
        :term:`ExtendedVersionAdminMixin`. Defined as a list of dictionaries,
        each mapping a model to a dictionary of ``{field: function}``.
