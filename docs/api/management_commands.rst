Management Commands
====================

djangocms-versioning provides management commands to help with version management and maintenance.


create_versions
---------------

Creates ``Version`` objects for versioned content that does not have a version assigned. This command is typically used:

- During initial setup of versioning on existing content
- After migrations if something goes wrong
- As a recovery tool if Version objects are missing


When to Use
+++++++++++

Use this command in these scenarios:

1. **Initial versioning setup**: You have existing content in your database and you're adding versioning support.

2. **After migrations**: If a migration fails or is rolled back, leaving content without Version objects.

3. **Recovery from data loss**: If Version objects have been accidentally deleted (when ``DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS`` is True).

4. **Multi-app versioning**: When adding versioning to additional models after the initial setup.


Basic Usage
+++++++++++

.. code-block:: bash

    # Create versions with default settings
    python manage.py create_versions --userid 1

    # Create versions as a specific user
    python manage.py create_versions --username admin

    # Test without making changes (dry-run)
    python manage.py create_versions --userid 1 --dry-run


Command Options
+++++++++++++++

.. list-table:: create_versions Options
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--state {draft,published,archived}``
     - State to assign to newly created versions (default: draft). Cannot be "unpublished"
   * - ``--username USERNAME``
     - Username of the user who will be the author of created versions
   * - ``--userid USERID``
     - User ID of the user who will be the author of created versions
   * - ``--dry-run``
     - Preview what would happen without making changes to the database
   * - ``-v {0,1,2,3}``
     - Verbosity level


State Assignment Logic
++++++++++++++++++++++

The command intelligently assigns states to versions:

1. If no versions exist for a grouper, content gets the requested state (default: ``draft``)
2. If a version already exists with the requested state, new content is assigned ``archived``
3. Only one version per grouper can have ``draft`` or ``published`` state at a time


**Example**: You have a Post with one existing published version. Running::

    python manage.py create_versions --state draft --userid 1

Would create a version with state ``archived`` (not draft) because draft must be unique.


User Specification
++++++++++++++++++

You must specify who created the versions. In order of precedence:

1. **DJANGOCMS_VERSIONING_DEFAULT_USER setting** (if set, cannot be overridden)
2. **--userid option** (command line user ID)
3. **--username option** (command line username)

If none are provided and there's content to version, the command fails:

.. code-block:: bash

    # This will fail if there's unversioned content and no default user is set
    python manage.py create_versions

    # Error: "Please specify a user which missing Version objects shall belong to"


Configuration Option
++++++++++++++++++++

To avoid having to specify a user every time, set in your settings:

.. code-block:: python

    # settings.py
    DJANGOCMS_VERSIONING_DEFAULT_USER = 1  # pk of the migration/default user

Then you can run::

    python manage.py create_versions


Common Scenario
---------------

When adding versioning to an existing model with existing content:

.. code-block:: bash

    # Create a migration user if you don't have one
    python manage.py shell
    >>> from django.contrib.auth import get_user_model
    >>> User = get_user_model()
    >>> migration_user = User.objects.create_user('migration', 'migration@example.com', 'password')
    >>> print(migration_user.pk)
    1

    # Exit shell and first identify the changes
    python manage.py create_versions --userid 1 --dry-run

    # Then run create_versions
    python manage.py create_versions --userid 1

    # Or set it as default and run without specifying
    python manage.py create_versions


Integrating with Migrations
----------------------------

You can call this command from a Django migration for automatic setup:

.. code-block:: python

    # yourapp/migrations/0005_add_versioning.py
    from django.core.management import call_command
    from django.db import migrations

    def create_versions_for_migration(apps, schema_editor):
        call_command('create_versions', userid=1)

    class Migration(migrations.Migration):
        dependencies = [
            ('yourapp', '0004_previous_migration'),
        ]

        operations = [
            migrations.RunPython(create_versions_for_migration),
        ]


.. note::

    When using in migrations, it's better to set ``DJANGOCMS_VERSIONING_DEFAULT_USER``
    in settings so you don't have to hardcode user IDs in migrations.
