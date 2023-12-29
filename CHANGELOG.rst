=========
Changelog
=========


2.0.0 (2023-12-29)
==================

What's Changed
--------------
* ci: Added concurrency to workflows by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/271
* ci: Remove ``os`` from test workflow matrix by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/270
* ci: Update actions to latest versions by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/269
* ci: Update isort params for v5 by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/268
* Add CodeQL workflow for GitHub code scanning by @lgtm-com in https://github.com/django-cms/djangocms-versioning/pull/297
* feat: Django 4.0, 4.1 / Python 3.10/3.11, mysql support, running tests on sqlite, postgres and mysql by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/287
* feat: Compat with cms page content extension changes by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/291
* fix: Additional change missed in #291 by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/301
* Add: Allow simple version management commands from the page tree indicator drop down menus by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/295
* fix: Adds compatibility for User models with no username field [#292] by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/293
* feat: Use same icons in page tree state indicators and Manage verisons by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/302
* fix: Remove patching the django CMS core by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/300
* fix: test requirements after removing the patching pattern by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/303
* feat: add localization and transifex support by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/305
* feat: Add management command to create version objects by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/304
* feat: add Dutch translations, transifex integration file by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/306
* feat: French localization by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/307
* feat: Albanian localization, Transifex integration by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/308
* Some fixed strings are now translatable by @svandeneertwegh in https://github.com/django-cms/djangocms-versioning/pull/310
* Translate '/djangocms_versioning/locale/en/LC_MESSAGES/django.po' in 'de' by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/311
* Translate '/djangocms_versioning/locale/en/LC_MESSAGES/django.po' in 'nl' by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/312
* fix: translation inconsistencies by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/313
* feat: Add preview button to view published mode by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/316
* feat: Huge performance improvement for admin_manager by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/318
* fix: Minor usability improvements by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/317
* fix: update messages by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/321
* Translate 'djangocms_versioning/locale/en/LC_MESSAGES/django.po' in 'de' by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/322
* fix: deletion of version objects blocked by source fields by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/320
* feat: allow reuse of status indicators by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/319
* fix: burger menu to also work with new core icons by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/323
* Translate 'djangocms_versioning/locale/en/LC_MESSAGES/django.po' in 'nl' by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/328
* ci: Switch flake8 and isort for ruff by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/329
* fix: Added related_name to version content type field by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/274
* feat: Django 4.2, Django CMS 4.1.0rc2 compatibility, and version locking by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/326
* Translations for djangocms_versioning/locale/en/LC_MESSAGES/django.po in de by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/330
* Translations for djangocms_versioning/locale/en/LC_MESSAGES/django.po in nl by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/331
* fix: Modify language menu for pages only if it is present by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/333
* feat: Add pypi actions by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/335
* feat: Reversable generic foreign key lookup from version by @Aiky30 in https://github.com/django-cms/djangocms-versioning/pull/241
* Add caching to PageContent __bool__ by @stefanw in https://github.com/django-cms/djangocms-versioning/pull/346
* Fix tests by @FinalAngel in https://github.com/django-cms/djangocms-versioning/pull/349
* Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in fr on branch master by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/347
* docs: List `DJANGOCMS_VERSIONING_LOCK_VERSIONS`  in settings by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/350
* docs: Update documentation by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/351
* fix: Update templates for better styling w/o djangocms-admin-style by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/352
* fix: PageContent extension's `copy_relations` method not called by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/344
* Bugfix/use keyword arguments in admin render change form method by @vipulnarang95 in https://github.com/django-cms/djangocms-versioning/pull/356
* Provide additional information when sending publish/unpublish events by @GaretJax in https://github.com/django-cms/djangocms-versioning/pull/348
* fix: Preview link language by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/357
* docs: Document version states by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/362
* feat: Add configuration to manage redirect on publish by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/358

New Contributors
----------------
* @marksweb made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/271
* @fsbraun made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/287
* @svandeneertwegh made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/310
* @stefanw made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/346
* @FinalAngel made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/349
* @vipulnarang95 made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/356
* @GaretJax made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/348

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
