Welcome to "djangocms-versioning"'s documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Tutorials:

   introduction/basic_concepts
   introduction/working_with_pages
   introduction/versioning_integration

.. toctree::
   :maxdepth: 2
   :caption: How-To Guides:

   howto/permissions
   howto/version_locking

.. toctree::
   :maxdepth: 2
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
   :caption: Explanation:

   explanations/admin_options
   explanations/customizing_version_list

.. toctree::
   :maxdepth: 2
   :caption: Release notes:

   upgrade/2.4.0
   upgrade/2.0.0


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

    grouper model
        A model with a one2many relationship with the
        :term:`content model <content model>`. An instance of the grouper
        model groups all the versions of one object. It is in effect the
        object being versioned. It also stores data that is not version-specific.

    extra grouping field
        The :term:`content model <content model>` must always have a foreign key
        to the :term:`grouper model <grouper model>`. However, the content model
        can also have additional grouping fields. This is how versioning
        is implemented for the ``cms.PageContent`` model, where ``PageContent.language``
        is defined as an extra grouping field. This supports filtering of objects
        by both its grouper object and its extra grouping fields in the admin and
        in any other implementations (in the page example, this ensures that
        the latest version of a German alias would not be displayed on an English page).

    copy function
        When creating a new draft version, versioning will usually copy an
        existing version. By default it will copy the current published version,
        but when reverting to an old version, a specific unpublished or archived version
        will be used. A customizable copy function is used for this.

    cms_config
        The ``cms_config.py`` file in a Django app that defines how the app
        integrates with django CMS and djangocms-versioning. It contains a
        ``CMSAppConfig`` subclass with versioning settings.

    ExtendedVersionAdminMixin
        A mixin class for Django admin that adds versioning-related fields and
        actions to the admin interface, including author, modified date,
        versioning state, and version management actions.

    extended_admin_field_modifiers
        A configuration option in :term:`cms_config` that allows customizing
        how fields are displayed in admin views that use the
        :term:`ExtendedVersionAdminMixin`. Defined as a dictionary mapping
        models to field transformation functions.
