Settings for djangocms Versioning
=================================

All Django CMS Versioning settings are optional and have sensible defaults. Add them to your Django ``settings.py`` file as needed.


.. py:attribute:: DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS

    **Default**: ``False``

    **Type**: boolean

    Controls whether users can delete version objects.

    When ``False`` (default):
        - Version objects that are the source of another version are protected from deletion
        - This preserves version history and prevents data corruption
        - The latest version (not a source for any other) can still be deleted

    When ``True``:
        - Users with appropriate permissions can delete any version object
        - Set this only if you don't need a full version history
        - Use with caution as it can break the version chain

    **Example**::

        # settings.py
        DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True

    **Related**: See the "Deletion protection" section in the :ref:`upgrade-to-2-0-0` release notes for more information.


.. py:attribute:: DJANGOCMS_VERSIONING_LOCK_VERSIONS

    **Default**: ``False``

    **Type**: boolean

    .. versionadded:: 2.0
        Before version 2.0, version locking was provided by a separate package.

    Enables draft version locking.

    When ``True``:
        - When a draft version is created, it becomes locked to its author
        - Only the author can edit the draft
        - The lock is automatically removed when the draft is published
        - Users with ``delete_versionlock`` permission can manually unlock versions
        - Unlocking sends a notification email to the original author

    When ``False`` (default):
        - Drafts are not locked
        - Any user with change permissions can edit any draft

    **Example**::

        # settings.py
        DJANGOCMS_VERSIONING_LOCK_VERSIONS = True

    **Related**: See :ref:`locking-versions` for complete information.


.. py:attribute:: DJANGOCMS_VERSIONING_USERNAME_FIELD

    **Default**: ``"username"``

    **Type**: string

    The name of the username field on your custom User model.

    Use this if your custom User model has a different username field name.

    **Example**::

        # settings.py for custom user model with 'email' as username
        DJANGOCMS_VERSIONING_USERNAME_FIELD = "email"

    **Related**: Only needed if using a :doc:`custom user model <django:topics/auth/customizing>`.


.. py:attribute:: DJANGOCMS_VERSIONING_DEFAULT_USER

    **Default**: ``None``

    **Type**: integer (user pk) or None

    The primary key of the default user to use when creating versions via management commands or migrations.

    When set, the ``create_versions`` management command doesn't require ``--userid`` or ``--username`` options.

    **Example**::

        # settings.py
        # If you have a system user with pk=1
        DJANGOCMS_VERSIONING_DEFAULT_USER = 1

    **Usage**::

        # With this setting, just run:
        python manage.py create_versions

        # Without it, you'd need:
        python manage.py create_versions --userid 1

    **Related**: See :doc:`api/management_commands` for more information.

    **Note**: If this setting is configured, command-line options ``--userid`` and ``--username`` are ignored.


.. py:attribute:: DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT

    **Default**: ``"published"``

    **Type**: string

    .. versionadded:: 2.0
        Before version 2.0, the behavior was always ``"versions"``.

    Determines where users are redirected after publishing or unpublishing content.

    **Allowed values**:

    - ``"versions"``: Redirect to the version overview of the current object
      - Useful for advanced users who need to track multiple versions
      - Shows all versions with their states

    - ``"published"``: Redirect to the content object on the site
      - Uses the object's ``.get_absolute_url()`` method
      - Falls back to preview URL if no absolute URL exists or if unpublishing

    - ``"preview"``: Redirect to the content object's preview endpoint
      - Shows what the content looks like on the site
      - Useful for content creators who want to verify their changes

    **Example**::

        # settings.py
        # Redirect to version overview after publish
        DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "versions"

        # Redirect to published page
        DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"

        # Redirect to preview
        DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "preview"

    **Recommendation**: Choose based on your workflow:
        - Content creators: ``"published"`` or ``"preview"`` for immediate feedback
        - Advanced editors managing many versions: ``"versions"`` for overview


.. py:attribute:: DJANGOCMS_VERSIONING_VERBOSE_UI

    **Incorrect name in conf.py**: ``DJANGOCMS_VERSIONING_VERBOSE``

    **Default**: ``True``

    **Type**: boolean

    **Note**: There's a typo in conf.py where the setting is named ``DJANGOCMS_VERSIONING_VERBOSE`` but should be ``DJANGOCMS_VERSIONING_VERBOSE_UI``.

    Controls the verbosity of the versioning UI in the admin.

    When ``True`` (default):
        - Version creation dates are displayed in the "manage versions" view
        - Version admin links appear in the Django admin index page
        - Full verbose UI is shown

    When ``False``:
        - Minimal, simplified UI
        - Creation dates hidden in version view
        - No entries in admin index page
        - Version management still accessible through CMS toolbar

    **Example**::

        # settings.py
        # Use simplified UI
        DJANGOCMS_VERSIONING_VERBOSE_UI = False

    **Use case**: Simplified UI can be useful for organizations with many users where a less verbose interface reduces cognitive load.


.. py:attribute:: EMAIL_NOTIFICATIONS_FAIL_SILENTLY

    **Default**: ``False``

    **Type**: boolean

    Controls error handling for version lock notification emails.

    When ``True``:
        - Email send failures are silently ignored
        - Useful for development or testing environments
        - Version operations complete even if email fails

    When ``False`` (default):
        - Email exceptions propagate to the caller
        - Failures are logged and visible

    **Example**::

        # settings.py
        # For development where email might not be configured
        EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True

    **Related**: Only relevant when ``DJANGOCMS_VERSIONING_LOCK_VERSIONS = True``.


.. py:attribute:: DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION

    **Default**: Depends on django CMS version
        - ``True`` for django CMS <= 4.1.0
        - ``False`` for django CMS 5.x and later

    **Type**: boolean

    Controls whether djangocms-versioning registers itself in the CMS menu.

    This is automatically managed based on your django CMS version and rarely needs to be configured manually.

    **Advanced use only**: Don't set this unless you have a specific reason to override the default behavior.


Settings Summary Table
----------------------

.. list-table:: All Djangocms-versioning Settings
   :widths: 30 20 50
   :header-rows: 1

   * - Setting Name
     - Default
     - Purpose
   * - ``DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS``
     - ``False``
     - Allow deletion of version objects
   * - ``DJANGOCMS_VERSIONING_LOCK_VERSIONS``
     - ``False``
     - Lock draft versions to their author
   * - ``DJANGOCMS_VERSIONING_USERNAME_FIELD``
     - ``"username"``
     - Custom user model username field name
   * - ``DJANGOCMS_VERSIONING_DEFAULT_USER``
     - ``None``
     - Default user for management commands
   * - ``DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT``
     - ``"published"``
     - Where to redirect after publish/unpublish
   * - ``DJANGOCMS_VERSIONING_VERBOSE_UI``
     - ``True``
     - Show verbose admin UI
   * - ``EMAIL_NOTIFICATIONS_FAIL_SILENTLY``
     - ``False``
     - Handle email errors silently
   * - ``DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION``
     - Auto-detected
     - Register in CMS menu


Complete Configuration Example
-------------------------------

.. code-block:: python

    # settings.py - djangocms-versioning configuration

    # Security: Protect version history from accidental deletion
    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = False

    # UX: Lock drafts to prevent conflicts
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True

    # Setup: Default user for migrations and commands
    DJANGOCMS_VERSIONING_DEFAULT_USER = 1  # pk of system user

    # UX: Redirect to the published page after changes
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"

    # UI: Show full UI with dates and admin index
    DJANGOCMS_VERSIONING_VERBOSE_UI = True

    # Email: Fail silently in development
    if DEBUG:
        EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True
    else:
        EMAIL_NOTIFICATIONS_FAIL_SILENTLY = False

    # Custom user model with email as username
    if AUTH_USER_MODEL != "auth.User":
        DJANGOCMS_VERSIONING_USERNAME_FIELD = "email"


Common Configuration Patterns
------------------------------

Production Setup
++++++++++++++++

.. code-block:: python

    # Production: Maximum protection and tracking
    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = False
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True
    DJANGOCMS_VERSIONING_DEFAULT_USER = 1
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"
    DJANGOCMS_VERSIONING_VERBOSE_UI = True
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = False


Development Setup
+++++++++++++++++

.. code-block:: python

    # Development: More flexibility, simplified UI
    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = False
    DJANGOCMS_VERSIONING_VERBOSE_UI = False
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True


Content Creator Focused
++++++++++++++++++++++++

.. code-block:: python

    # Focus on ease of use for content creators
    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True  # Prevent edit conflicts
    DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT = "published"  # See result
    DJANGOCMS_VERSIONING_VERBOSE_UI = False  # Simple interface
