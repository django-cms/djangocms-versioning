=========
Changelog
=========


Unreleased
==========
* fix: Add keyword arguments in VersionAdminMixin render_change_form
* feat: Reversable generic foreign key lookup from version
* feat: Provide additional information about unpublished/published versions when sending signals
* fix: formatted files through ruff to fix tests
* fix: Remove version check when evaluating CMS PageContent objects

2.0.0rc1
========
* fix: Only try modifying page language menu if it is present
* fix: Added ``related_name`` attribute to the ``content_type`` foreign key of the ``Version`` model.
* fix: burger menu adjusts to the design of django cms core dropdown
* fix: bug that showed an archived version as unpublished in some cases in the state indicator
* add: Dutch and French translations thanks to Stefan van den Eertwegh and François Palmierso
* add: transifex support, German translations
* add: Revert button as replacement for dysfunctional Edit button for unpublished
  versions
* add: status indicators and drop down menus for django cms page tree
* fix: only offer languages for plugin copy with available content
* feat: Add support for Django 4.0, 4.1 and Python 3.10 and 3.11
* fix: migrations for MySql
* ci: Updated isort params in lint workflow to meet current requirements.
* ci: Update actions to v3 where possible, and coverage to v2 due to v1 sunset in Feb
* ci: Remove ``os`` from test workflow matrix because it's unused
* ci: Added concurrency option to cancel in progress runs when new changes occur
* fix: Added setting to make the field to identify a user configurable in ``ExtendedVersionAdminMixin.get_queryset()`` to fix issue for custom user models with no ``username``
* ci: Run tests on sqlite, mysql and postgres db

* feat: Compatibility with page content extension changes to django-cms
* ci: Added basic linting pre-commit hooks

1.2.2 (2022-07-20)
==================
* fix: Admin burger menu excluding Preview and Edit buttons in all languages

1.2.1 (2022-06-13)
==================
* fix: Added correct relationship description to get_created_by admin_order_field

1.2.0 (2022-06-09)
==================
* feat: Add View Published button for page edit or preview mode

1.1.0 (2022-06-08)
==================
* feat: Added injection point for field modification in the ExtendedAdminMixin

1.0.6 (2022-05-31)
==================
* fix: Version Changelist table edit button opens all items out of the sideframe

1.0.5 (2022-05-27)
==================
* fix: Sideframe always closing when it has been specified to stay open

1.0.4 (2022-04-05)
==================
* feat: Added a burger menu in the actions column of the ExtendedVersionAdminMixin.

1.0.3 (2022-03-18)
==================
* Enable django messages to be hidden after set timeout

1.0.2 (2022-03-03)
==================
* Fix: Updated icon base template to include proper closesideframe tag

1.0.1 (2022-03-03)
==================
* feat: Open compare view in new tab
* Hiding the back button in compare view

1.0.0 (2022-02-23)
==================
* Python 3.8, 3.9 support added
* Django 3.0, 3.1 and 3.2 support added
* Python 3.5 and 3.6 support removed
* Django 1.11 support removed

0.0.33 (2022-01-11)
===================
* fix: Page Content Extended models do no update the version modified date as they should.

0.0.32 (2022-01-05)
===================
* fix: Added field ordering to the generic versioning admin mixin

0.0.31 (2021-11-24)
===================
* fix: Remove forcing a Timezone (USE_TZ=False) for the test suite which doesn't help for projects where the TZ is not forced to True.
* feat: Replaced CircleCI with GitHub Actions for the automated test suite.

0.0.30 (2021-11-17)
===================
* feat: django-cms TitleExtension admin save fix and extended PageContent copy method that copies extensions
