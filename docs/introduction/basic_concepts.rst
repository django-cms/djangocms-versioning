Introduction
============

djangocms-versioning is a general purpose package that manages versions
for page contents and other models within four categories: **published**,
**draft**, **unpublished**, or **archived**, called "version states".


Version states
--------------

Each versioned object carries a version number, creation date, modification date, a reference to the user who created the version, and **version state**. The states are:

  * **draft**: This is the version which currently can be edited. Only draft versions can
    be edited and only one draft version per language is allowed. Changes made to draft
    pages are not visible to the public.
  * **published**: This is the version currently visible on the website to the public. Only
    one version per language can be public. It cannot be changed. If it needs to be changed
    a new draft is created based on a published page and the published page stays unchanged.
  * **unpublished**: This is a version which was published at one time but now is not
    visible to the public any more. There can be many unpublished versions.
  * **archived**: This is a version which has not been published and therefore has never been
    visible to the public. It represents a state which is intended to be used for
    later work (by reverting it to a draft state).

Each new draft version will generate a new version number.

.. image:: /static/version-states.png
     :align: center
     :alt: Version states

When an object is published, it changes state to **published** and thereby becomes publicly visible. All other version states are invisible to the public.

Effect on the model's manager
-----------------------------

When handling versioned models in code, you'll generally only "see" published objects:

.. code-block::

    MyModel.objects.filter(language="en")   # get all published English objects of MyModel

will return a queryset with published objects only. This is to ensure that no draft or unpublished versions leak or become visible to the public.

Since often draft contents are the ones you interact with in the admin interface, or in draft mode in the CMS frontend, djangocms-versioning introduces an additional model manager for the versioned models **which may only be used on admin sites and admin forms**::

    MyModel.admin_manager.filter(language="en")

will retrieve all objects of all versions. Alternativley, to get the current draft version you can to filter the ``Version`` object::

    from djangocms_versioning.constants import DRAFT

    MyModel.admin_manager.filter(language="en", versions__status==DRAFT)

Finally, there are instance where you want to access the "current" version of a page. This is either the current draft version or - there is no draft - the published version. You can easily achieve this by using::

    MyModel.admin_manager.filter(language="en").current_content()
