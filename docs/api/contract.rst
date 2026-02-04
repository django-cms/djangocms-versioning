.. _versioning_contract:

Versioning contract
===================

Django CMS uses a contract-based approach for versioning, allowing different versioning
implementations to integrate with the CMS and its ecosystem. **djangocms-versioning defines
the versioning contract** for django CMS. This section describes the contract that
djangocms-versioning does implement and other versioning packages must implement to work
with django CMS.

Overview
--------

The contract is implemented through django CMS's ``CMSAppExtension`` mechanism in the
``cms_config.py`` module. When installed, djangocms-versioning becomes the versioning
provider for all content types that register with it—including django CMS pages,
aliases, stories, and any custom content models.

.. note::

    **djangocms-versioning** is the reference implementation endorsed by the django CMS
    Association.

Contract definition
-------------------

The contract is defined in djangocms-versioning's ``cms_config.py`` using the
``contract`` class attribute, a 2-tuple consisting of the contract name (``"djangocms_versioning"``)
and the contract class (``VersionableItem``):

.. code-block:: python

    from cms.app_base import CMSAppExtension
    from .datastructures import VersionableItem

    class VersioningCMSExtension(CMSAppExtension):
        contract = "djangocms_versioning", VersionableItem

        def __init__(self):
            self.versionables = []

        def configure_app(self, cms_config):
            # Process the versioning configuration
            if hasattr(cms_config, "versioning"):
                self.handle_versioning_setting(cms_config)
                # ... additional setup

The ``contract`` attribute is a tuple of:

1. The contract name (``"djangocms_versioning"``)
2. The ``VersionableItem`` class that apps use to register their content models

This allows other packages to register for versioning without importing directly from
djangocms-versioning, enabling alternative implementations to provide the same contract.

Contract components
-------------------

VersionableItem class
~~~~~~~~~~~~~~~~~~~~~

The ``VersionableItem`` class defines how a content model participates in versioning.
At minimum, it must accept:

``content_model``
    The Django model class that stores versioned content (the :term:`content model`).

``grouper_field_name``
    The name of the foreign key field on the content model that points to the
    :term:`grouper model`.

``copy_function``
    An (optional) callable that creates a copy of a content object when creating new versions.

Additional optional parameters are djangocms-versioning-specific and may include:

- ``extra_grouping_fields``: Additional fields for grouping versions (e.g., ``language``)
- ``on_publish``, ``on_unpublish``, ``on_draft_create``, ``on_archive``: Lifecycle hooks
- ``preview_url``: Function to generate preview URLs for versions
- ``content_admin_mixin``: Custom admin mixin for the content model
- ``grouper_admin_mixin``: Custom admin mixin for the grouper model

Manager modifications
~~~~~~~~~~~~~~~~~~~~~

A versioning package typically modifies the content model's managers:

``objects`` manager
    Should filter to return only published content by default, ensuring unpublished
    content never leaks to the public.

``admin_manager``
    Should provide access to all content versions, for use in admin contexts only.

These managers enable the pattern:

.. code-block:: python

    # Public queries - only published content
    PostContent.objects.filter(...)

    # Admin queries - all versions accessible
    PostContent.admin_manager.filter(...)

Registration mechanism
----------------------

Content models register for versioning via ``cms_config.py``:

.. code-block:: python

    # myapp/cms_config.py
    from cms.app_base import CMSAppConfig

    from .models import MyContent


    class MyAppConfig(CMSAppConfig):
        djangocms_versioning_enabled = True  # <contract>_enabled = True

        def __init__(self, app):
            super().__init__(app)

            # Dynamically get the installed contract object
            VersionableItem = self.get_contract("djangocms_versioning")

            self.versioning = [
            VersionableItem(
                content_model=MyContent,
                grouper_field_name="grouper",
                grouper_admin_mixin="__default__",
            ),
        ]

The ``djangocms_versioning_enabled = True`` attribute signals that this app wants to
use the versioning extension. The ``get_contract("djangocms_versioning")`` call retrieves the
``VersionableItem`` class from the installed versioning package, allowing the app to
register its content models for versioning.

Implementing alternative versioning packages
--------------------------------------------

Alternative versioning packages must follow the contract defined by djangocms-versioning.
Specifically, they must:

1. **Export a VersionableItem class** (or compatible equivalent) that other packages
   can discover and use for registration.

2. **Process the** ``versioning`` **attribute** from ``CMSAppConfig`` subclasses that
   have ``djangocms_versioning_enabled = True``.

3. **Modify content model managers** to provide the ``objects`` / ``admin_manager``
   pattern expected by django CMS and ecosystem packages.

4. **(Optional) Provide version state information** for the CMS toolbar and admin
   interfaces. djangocms-versioning does this by injecting a ``content_indicator``
   method onto content models that returns status strings (e.g., ``"published"``,
   ``"draft"``, ``"dirty"``). Alternative implementations may define their own states
   or omit this functionality.

Ecosystem compatibility
-----------------------

Packages in the django CMS ecosystem (such as djangocms-alias and djangocms-stories)
register their content models using the versioning contract. When you install a
versioning package, it becomes responsible for managing versions of *all* registered
content types.

This means:

- Switching versioning packages affects all versioned content across your site
- Alternative implementations must handle registrations from ecosystem packages
- The version states and workflow defined by your versioning package apply universally

See also
--------

- :doc:`/introduction/versioning_integration` for integrating your models with versioning
- :doc:`advanced_configuration` for customizing versioning behavior
- :doc:`models` for the Version model reference
