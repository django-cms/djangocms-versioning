Management command
==================

create_versions
---------------

``create_versions`` creates ``Version`` objects for versioned content that does
not have a version assigned. This happens if djangocms-versioning is added to
content models after content already has been created.

By default, the existing content is assigned the draft status.

Each version is assigned a user who created the version. When this command is
run, either

* the user is taken from the ``DJANGOCMS_VERSIONING_DEFAULT_USER`` setting
  which must contain the primary key (pk) of the user, or
* one of the options ``--userid`` or ``--username``

If ``DJANGOCMS_VERSIONING_DEFAULT_USER`` is set it cannot be overridden by a
command line option.

.. code-block:: shell

    usage: manage.py create_versions [-h]
                                 [--state {draft,published,unpublished,archived}]
                                 [--username USERNAME] [--userid USERID]
                                 [--dry-run]

    Creates Version objects for versioned models lacking one. If the
    DJANGOCMS_VERSIONING_DEFAULT_USER setting is not populated you
    will have to provide either the --userid or --username option for
    each Version object needs to be assigned to a user.

    optional arguments:
      -h, --help            show this help message and exit
      --state {draft,published,unpublished,archived}
                            state of newly created version object
                            (defaults to draft)
      --username USERNAME   Username of user to create the missing
                            Version objects
      --userid USERID       User id of user to create the missing
                            Version objects
      --dry-run             Do not change the database
