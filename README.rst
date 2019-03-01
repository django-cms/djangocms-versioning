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

Versioning integration instructions are available in `docs/versioning_integration.rst <docs/versioning_integration.rst>`_

An example implementation can be found here:

- `djangocms_versioning/test_utils/polls/cms_config.py <djangocms_versioning/test_utils/polls/cms_config.py>`_
- `djangocms_versioning/test_utils/polls/models.py <djangocms_versioning/test_utils/polls/models.py>`_


Documentation
=============

We maintain documentation under ``docs`` folder using rst format. HTML documentation can generate using following command

Run::

    cd docs/
    make html

This should generate all html files from rst documents under `docs/_build` folder, which can be browsed.

