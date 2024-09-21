|django| |djangocms4|

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

    python -m manage migrate djangocms_versioning
    python -m manage create_versions --user-id <user-id-of-migration-user> 

to perform the application's database migrations and (only if you have an existing database) add version objects
needed to mark existing versions as draft.


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

============
Contributing
============

Because this is a an open-source project, we welcome everyone to
`get involved in the project <https://www.django-cms.org/en/contribute/>`_ and
`receive a reward <https://www.django-cms.org/en/bounty-program/>`_ for their contribution.
Become part of a fantastic community and help us make django CMS the best CMS in the world.

We'll be delighted to receive your
feedback in the form of issues and pull requests. Before submitting your
pull request, please review our `contribution guidelines
<http://docs.django-cms.org/en/latest/contributing/index.html>`_.

The project makes use of git pre-commit hooks to maintain code quality.
Please follow the installation steps to get `pre-commit <https://pre-commit.com/#installation>`_
setup in your development environment.

We're grateful to all contributors who have helped create and maintain
this package. Contributors are listed at the `contributors
<https://github.com/django-cms/djangocms-versioning/graphs/contributors>`_
section.

One of the easiest contributions you can make is helping to translate this addon on
`Transifex <https://www.transifex.com/divio/django-cms-versioning/dashboard/>`_.
To update transifex translation in this repo you need to download the
`transifex cli <https://developers.transifex.com/docs/cli>`_ and run
``tx pull`` from the repo's root directory. After downloading the translations
do not forget to run the ``compilemessages`` management command.


.. |django| image:: https://img.shields.io/badge/django-3.2%2B-blue.svg
    :target: https://www.djangoproject.com/
.. |djangocms4| image:: https://img.shields.io/badge/django%20CMS-4.1-blue.svg
    :target: https://www.django-cms.org/
