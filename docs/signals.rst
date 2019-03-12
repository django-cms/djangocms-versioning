Signals
=======

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Signals are fired before and after the following events which can be found in the file 'constants.py': 
    - When a version is created the operation sent is 'operation_draft'
    - When a version is archived the operation sent is 'operation_archive'
    - When a version is published the operation emitted is 'operation_publish'
    - When a version is un-published the operation emitted is 'operation_unpublish'

A token is emitted in the signals that will allow the pre and post signals to be tied together, this could be of use if multiple transactions occur at the same time, allowing a token to match the pre and post signals that belong together.

How to use the version publish and un-publish signal for a CMS Page
---------------------------------------------------------------------

The CMS used to provide page publish and unpublish signals which have since been removed in DjangoCMS 4.0. To replicate the behaviour you can listen to changes on the cms model PageContent as shown in the example below.

.. code-block:: python

    from django.dispatch import receiver

    from cms.models import PageContent

    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation


    @receiver(post_version_operation, sender=PageContent)
    def do_something_on_page_publish_unpublsh(*args, **kwargs):

        if (kwargs['operation'] == constants.OPERATION_PUBLISH or
           kwargs['operation'] == constants.OPERATION_UNPUBLISH):
            # ... do something


