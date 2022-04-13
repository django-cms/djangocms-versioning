=========
Changelog
=========

Unreleased
==========
* feat: Added an action button to view the published content
* ci: Updated isort params in lint workflow to meet current requirements.
* ci: Updated workflows to use version 3

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
