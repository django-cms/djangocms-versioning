****************
django CMS Versioning
****************

============
Installation
============

Requirements
============

django CMS Versioning requires that you have a django CMS 4.0 (or higher) project already running and set up.


To install
==========

Run::

    pip install djangocms-versioning

Add ``djangocms_versioning`` to your project's ``INSTALLED_APPS``.

Run::

    python manage.py migrate djangocms_versioning

to perform the application's database migrations.


=====
Usage
=====

Versioning integration instructions are available in `docs/versioning_integration.md <docs/versioning_integration.md>`_

An example implementation can be found here:

- `djangocms_versioning/test_utils/polls/cms_config.py <djangocms_versioning/test_utils/polls/cms_config.py>`_
- `djangocms_versioning/test_utils/polls/models.py <djangocms_versioning/test_utils/polls/models.py>`_

