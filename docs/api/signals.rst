Signals
=======

Signals are fired before and after the following events which can be found in the file 'constants.py': 
    - When a version is created the operation sent is 'operation_draft'
    - When a version is archived the operation sent is 'operation_archive'
    - When a version is published the operation emitted is 'operation_publish'
    - When a version is un-published the operation emitted is 'operation_unpublish'

A token is emitted in the signals that will allow the pre and post signals to be tied together, this could be of use if multiple transactions occur at the same time, allowing a token to match the pre and post signals that belong together.

How to use the version publish and un-publish signal for a CMS Page
---------------------------------------------------------------------

The CMS used to provide page publish and unpublish signals which have since been removed in DjangoCMS 4.0. To replicate the behaviour you can listen to changes on the cms model PageContent as shown in the example below:

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


Handling the effect of a (un-)publish to other items via signals
----------------------------------------------------------------

Events often times do not happen in isolation. 
A publish signal indicates a publish of an item but it also means that potentially other items are unpublished as part of the same action, also triggering unpublish signals. 
To be able to react accordingly, information is added to the publish signal which other items were potentially unpublished as part of this action (`unpublished`) and information is also added to the unpublish singal which other items are going to get published (`to_be_published`). 
This information allows you to differentiate if an item is published for the first time - because nothing is unpublished - or if it is just a new version of an existing item.

For example, the differentiation can be benefitial if you integrate with other services like Elasticsearch and you want to update the Elasticsearch index via signals. You can get in the following situations:
    - Publish signal with no unpublished item results in a new entry in the index.
    - Publish signal with at least one unpublished item results in an update of an existing entry in the index.
    - Unpublish singal with no to be published items results in the removal of the entry from the index.
    - Unpublish signal with a to be published item results in the update on an existing entry in the index but will be handled in the corresponding publish signal and can be ignored.

All those situations are distinct, require different information, and can be handled according to requirements.
