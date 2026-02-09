=========
Changelog
=========

2.5.1 (2026-02-09)
==================

* feat: Allow "View on Site" for objects not on the current site by @stefanw in https://github.com/django-cms/djangocms-versioning/pull/479
* feat: Preserve GET params for "View published" button by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/509
* feat: Changelist performance improvement by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/505
* fix: Make copy_function optional by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/515
* fix: Invalid permission checking in ExtendedVersionAdminMixin by @pierreben in https://github.com/django-cms/djangocms-versioning/pull/519
* docs: Update api reference by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/508
* docs: Update docs to explain the djangocms_versioning contract by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/511
* docs: update signal parameters documentation by @nstuardod in https://github.com/django-cms/djangocms-versioning/pull/517
* locale: Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in fr by @transifex-integration[bot] in https://github.com/django-cms/djangocms-versioning/pull/513

**New Contributors**

* @nstuardod made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/517
* @pierreben made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/519

2.5.0 (2025-11-14)
==================

* feat: Language menu allows creating new translations from preview mode by @va-lang in https://github.com/django-cms/djangocms-versioning/pull/491
* feat: Modernize Python and Django support: Drop Python 3.9, add Python 3.14 and Django 6.0 by @vinitkumar in https://github.com/django-cms/djangocms-versioning/pull/489
* feat: Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in de by @transifex-integration[bot] in https://github.com/django-cms/djangocms-versioning/pull/496
* chore: Swap django-fsm with django-fsm-2
* fix: Typo in permission name by @stefan6419846 in https://github.com/django-cms/djangocms-versioning/pull/476
* fix: Remove unnecessary `_original_manager` usage from toolbar by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/477
* fix: Respect site-specific language configurations by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/480
* fix: Respect permissions for indicator menus and version locking by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/493

**New Contributors**

* @stefan6419846 made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/476
* @vinitkumar made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/489
* @va-lang made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/491

2.4.0 (2025-07-17)
==================

* feat: Auto-add versioning mixin to GrouperAdmin by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/472

2.3.2 (2025-05-16)
==================

* fix: Add back ``create_versions`` management commmand by @fsbraun in

2.3.1 (2025-05-13)
==================

* feat: Improve default copy method to also copy placeholders and plugins by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/345
* fix: Only show language menu for more than one language by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/457
* Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in nl by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/460
* Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in sq by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/463
* Updates for file djangocms_versioning/locale/en/LC_MESSAGES/django.po in ru by @transifex-integration in https://github.com/django-cms/djangocms-versioning/pull/459
* fix: Use consistent django colors for accent object tools by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/464
* chore: Remove deprecated django CMS references by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/465


2.2.1 (2025-03-06)
==================

* fix: Pre-populate `version.content` cache when getting version object by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/446
* fix: Test compatibility with django CMS 5 by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/453
* fix: For headless mode, django CMS 5.0 adds preview buttons to all views. Do not add again. by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/455
* ci: update ruff configuration by @earthcomfy in https://github.com/django-cms/djangocms-versioning/pull/448
* build(deps): bump actions/cache from 4.2.0 to 4.2.2 by @dependabot in https://github.com/django-cms/djangocms-versioning/pull/452


2.2.0 (2025-01-17)
==================

* feat: Added bulk delete to version change view by @polyccon in https://github.com/django-cms/djangocms-versioning/pull/338
* feat: Re-introduce deleting languages of a page by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/443
* feat: Autocomplete fields for grouper selection and option for less verbose UI by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/433
* fix: Unpublished or archived versions not shown in language menu by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/440
* fix: add resolvability check before redirecting to prevent insecure redirects after publishing by @theShinigami in https://github.com/django-cms/djangocms-versioning/pull/436
* fix: test.pypi.org workflow environment name by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/434
* fix: attempt to remove missing item from list by @jrief in https://github.com/django-cms/djangocms-versioning/pull/439
* fix: Take csrf token from CMS config if possible by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/444
* build(deps): bump codecov/codecov-action from 4 to 5 by @dependabot in https://github.com/django-cms/djangocms-versioning/pull/435
* build(deps): bump actions/cache from 4.0.2 to 4.1.2 by @dependabot in https://github.com/django-cms/djangocms-versioning/pull/431
* build(deps): bump actions/cache from 4.1.2 to 4.2.0 by @dependabot in https://github.com/django-cms/djangocms-versioning/pull/438

**New Contributors**

* @polyccon made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/338
* @theShinigami made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/436

2.1.0 (2024-07-12)
==================

* feat: add support for Django 5.0 and 5.1 (#429) by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/429
* feat: Add versioning actions to settings (admin change view) of versioned objects by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/408
* fix: Remove workaround for page-specific rendering by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/411
* fix: Compare versions' back button sometimes returns to invalid URL by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/413


* feat: Add versioning actions to settings (admin change view) of versioned objects by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/408
* feat: Optimize db evaluation by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/416
* feat: Prefetch page content version objects for faster page tree by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/418
* fix: Remove workaround for page-specific rendering by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/411
* fix: Compare versions' back button sometimes returns to invalid URL by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/413
* fix: Preparation for changes in django CMS 4.2 by @jrief in https://github.com/django-cms/djangocms-versioning/pull/419
* fix: Unnecessary complexity in ``current_content`` query set by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/417
* fix: get_page_content retrieved non page-content objects from the toolbar by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/423


**Full Changelog**: https://github.com/django-cms/djangocms-versioning/compare/2.0.2...2.1.0

2.0.2 (2024-05-03)
==================

* fix: Do not show edit action for version objects where editing is not possible by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/405
* feat: Add Arabic locale

2.0.1 (2024-03-29)
==================

* feat: Add content object level publish permissions by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/390
* fix: Create missing __init__.py in management folder by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/366
* fix #363: Better UX in versioning listview by @jrief in https://github.com/django-cms/djangocms-versioning/pull/364
* fix: Several fixes for the versioning forms: #382, #383, #384 by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/386
* fix: For Django CMS 4.1.1 and later do not automatically register versioned CMS Menu by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/388
* fix: Post requests from the side frame were sent to wrong URL by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/396
* fix: Consistent use of action buttons by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/392
* fix: Avoid duplication of placeholder checks for locked versions by @fsbraun in https://github.com/django-cms/djangocms-versioning/pull/393
* ci: Add testing against django main by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/353
* ci: Improve efficiency of ruff workflow by @marksweb in https://github.com/django-cms/djangocms-versioning/pull/378
* Chore: update ruff and pre-commit hook by @raffaellasuardini in https://github.com/django-cms/djangocms-versioning/pull/381
* build(deps): bump actions/cache from 4.0.1 to 4.0.2 by @dependabot in https://github.com/django-cms/djangocms-versioning/pull/397

New Contributors

* @raffaellasuardini made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/381
* @jrief made their first contribution in https://github.com/django-cms/djangocms-versioning/pull/364

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
