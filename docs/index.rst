Welcome to "djangocms-versioning"'s documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Quick Start:

   basic_concepts
   versioning_integration
   version_locking

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/advanced_configuration
   api/signals
   api/customizing_version_list
   api/management_commands
   settings

.. toctree::
   :maxdepth: 2
   :caption: Internals:

   admin_architecture

.. toctree::
   :maxdepth: 2
   :caption: Release notes:

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
