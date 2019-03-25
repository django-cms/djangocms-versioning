Welcome to "djangocms-versioning"'s documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Quick Start:

   versioning_integration

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   signals
   customizing_version_list

.. toctree::
   :maxdepth: 2
   :caption: Internals:

   admin_architecture


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
