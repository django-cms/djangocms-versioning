Management command
==================

create_versions
---------------

``create_versions`` creates ``Version`` objects for versioned content that does
not have a version assigned. This happens if djangocms-versioning is added to
content models after content already has been created. It can also be used as a
recovery tool if - for whatever reason - some or all ``Version`` objects have
not been created for a grouper.

By default, the existing content is assigned the draft status. If a draft
version already exists the content will be given the archived state.

Each version is assigned a user who created the version. When this command is
run, either

* the user is taken from the ``DJANGOCMS_VERSIONING_DEFAULT_USER`` setting
  which must contain the primary key (pk) of the user, or
* one of the options ``--userid`` or ``--username``

If ``DJANGOCMS_VERSIONING_DEFAULT_USER`` is set it cannot be overridden by a
command line option.

.. code-block:: shell

    usage: manage.py create_versions [-h] [--state {draft,published,archived}]
                                     [--username USERNAME] [--userid USERID] [--dry-run]
                                     [--version] [-v {0,1,2,3}] [--settings SETTINGS]
                                     [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                                     [--force-color] [--skip-checks]

    Creates Version objects for versioned models lacking one. If the
    DJANGOCMS_VERSIONING_DEFAULT_USER setting is not populated you will have to provide
    either the --userid or --username option for each Version object needs to be assigned
    to a user. If multiple content objects for a grouper model are found only the newest
    (by primary key) is assigned the state, older versions are marked as "archived".

    optional arguments:
      -h, --help            show this help message and exit
      --state {draft,published,archived}
                            state of newly created version object (defaults to draft)
      --username USERNAME   Username of user to create the missing Version objects
      --userid USERID       User id of user to create the missing Version objects
      --dry-run             Do not change the database
