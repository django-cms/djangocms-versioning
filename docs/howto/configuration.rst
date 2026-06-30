Configure versioning for your workflow
======================================

This guide shows ready-to-paste settings blocks for common situations. For the
full, neutral description of every setting, see :doc:`/api/settings`.


A complete, annotated configuration
-----------------------------------

.. code-block:: python

    # settings.py — djangocms-versioning configuration

    # Protect version history from accidental deletion
    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = False

    # Lock drafts to their author to prevent edit conflicts
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True

    # Default author for migrations and the create_versions command
    DJANGOCMS_VERSIONING_DEFAULT_USER = 1  # pk of a system user

    # Where to land after publishing — "published", "preview" or "versions"
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"

    # Show creation dates and admin-index links
    DJANGOCMS_VERSIONING_VERBOSE_UI = True

    # Don't let a misconfigured mailer break a publish in development
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = DEBUG

    # Custom user model that authenticates by email
    if AUTH_USER_MODEL != "auth.User":
        DJANGOCMS_VERSIONING_USERNAME_FIELD = "email"


Production
----------

Maximum protection and a full audit trail:

.. code-block:: python

    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = False
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True
    DJANGOCMS_VERSIONING_DEFAULT_USER = 1
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"
    DJANGOCMS_VERSIONING_VERBOSE_UI = True
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = False


Development
-----------

More flexibility, a simpler UI, and no mail surprises:

.. code-block:: python

    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = False
    DJANGOCMS_VERSIONING_VERBOSE_UI = False
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True


Editor-focused
--------------

Tuned for people who write content rather than manage versions:

.. code-block:: python

    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True            # no edit conflicts
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"  # see the result
    DJANGOCMS_VERSIONING_VERBOSE_UI = False              # fewer distractions

Pick ``"published"`` or ``"preview"`` for ``ON_PUBLISH_REDIRECT`` when editors
want immediate feedback; choose ``"versions"`` only for people who routinely
juggle many versions of the same object.
