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
+++++++++++++++

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
+++++++++++++++++++++++++++

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


delete_unpublished_versions
---------------------------

.. versionadded:: 2.8

Permanently deletes unpublished versions -- and the content objects behind them -- that
have not been touched for a given number of days (90 by default). Use it to keep the
version history of a long-running site from growing without bounds.

Draft and published versions are **never** deleted. Archived versions are only deleted
when ``--archived`` is given.

Because deleting versions is destructive, the command refuses to run unless
:attr:`DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS` is set to ``constants.DELETE_ANY``
or ``constants.DELETE_NON_PUBLIC_ONLY``::

    CommandError: Deleting versions is not enabled. Set
    DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS to "any" or "non-public only" in
    settings.py to allow this command to delete versions.

With ``constants.DELETE_NON_PUBLIC_ONLY`` an unpublished version that a published version
was created from stays protected: such versions are skipped and not reported as candidates.


Basic Usage
+++++++++++

.. code-block:: bash

    # See what a run would remove -- always do this first
    python manage.py delete_unpublished_versions --dry-run

    # Delete unpublished versions older than 90 days
    python manage.py delete_unpublished_versions

    # Delete unpublished and archived versions older than 30 days, unattended
    python manage.py delete_unpublished_versions --days 30 --archived --noinput


Command Options
+++++++++++++++

.. list-table:: delete_unpublished_versions Options
   :widths: 30 70
   :header-rows: 1

   * - Option
     - Description
   * - ``--days DAYS``
     - Only delete versions untouched for at least this many days (default: 90)
   * - ``--archived``
     - Also delete archived versions, not just unpublished ones
   * - ``--dry-run``
     - Report the number of affected versions per content model and exit without changing anything
   * - ``--model app_label.ModelName``
     - Limit the run to one content model. Repeat the option for several models
   * - ``--date-field {modified,created}``
     - Version field the age is measured on (default: ``modified``, i.e. the time the version
       was last changed, which for an unpublished version is when it was unpublished)
   * - ``--batch-size BATCH_SIZE``
     - Number of content objects processed per batch (default: 1000)
   * - ``--delete-empty-groupers``
     - Also delete grouper objects (e.g. a ``Poll`` or ``BlogPost``) that are left without any
       content object, mirroring what deleting the last version of a grouper does
   * - ``--noinput``, ``--no-input``
     - Do not prompt for confirmation before deleting
   * - ``-v {0,1,2,3}``
     - Verbosity level. ``2`` reports progress per batch


How Deletion Works
++++++++++++++++++

The command groups the matching versions by content type and processes the **content
objects** in batches. Models using Django's standard ``Model.delete()`` are deleted in bulk.
Models that override ``delete()`` (including inherited overrides) are deleted individually
through that method to preserve custom cleanup. Both paths retain Django's deletion signals
and cascades. The ``Version`` objects follow through the generic relation django CMS
Versioning injects into every versioned content model.

Content objects that another model protects through a foreign key cannot be deleted. The
command falls back to deleting the batch object by object, keeps the protected ones and
reports how many were kept::

    Deleted 412 version(s).
    3 version(s) were kept: their content object is protected by a foreign key.

With ``--delete-empty-groupers``, empty groupers are always deleted individually through
their model's ``delete()`` method. A protected grouper is kept without preventing other
empty groupers from being deleted. Content in any language or state keeps its grouper alive.

Page groupers are processed deepest-first and are only deleted when they have no remaining
descendants. This preserves descendants with retained content, as well as empty descendants
outside the cleanup candidates. An eligible empty branch is removed one page at a time,
preserving django CMS's tree maintenance and cache cleanup.


Running Regularly
+++++++++++++++++

The command is safe to run from cron or a scheduled task:

.. code-block:: bash

    # Every night at 3:00, prune unpublished and archived versions older than a year
    0 3 * * * /path/to/venv/bin/python /path/to/manage.py delete_unpublished_versions \
        --days 365 --archived --noinput -v 0

.. warning::

    Deleted versions cannot be restored. Run with ``--dry-run`` first and make sure you
    have a database backup before the first unattended run.
