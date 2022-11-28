*********************
django CMS Versioning
*********************

.. warning::

    This is the development branch for django CMS version 4.1 support.

    For django CMS V4.0 support, see `support/django-cms-4.0.x branch <https://github.com/django-cms/djangocms-versioning/tree/support/django-cms-4.0.x>`_


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


Testing
=======

To run all the tests the only thing you need to do is run

    pip install -r tests/requirements.txt
    python setup.py test


Documentation
=============

We maintain documentation under the ``docs`` folder using rst format.

To generate the HTML documentation you will need to install ``sphinx`` (``pip install sphinx``) and ``graphviz`` (as per your operating system's package management system). You can then generate the docs using the following command:

Run::

    cd docs/
    make html

This should generate all html files from rst documents under `docs/_build` folder, which can be browsed.

