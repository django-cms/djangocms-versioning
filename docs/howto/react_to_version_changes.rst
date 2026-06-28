React to version changes with signals
=====================================

djangocms-versioning fires :data:`~djangocms_versioning.signals.pre_version_operation`
and :data:`~djangocms_versioning.signals.post_version_operation` around every state
change. This guide collects recipes for common reactions. For the signal arguments,
operation constants and firing order, see :doc:`/api/signals`.


Invalidate a cache
------------------

.. code-block:: python

    from django.core.cache import cache
    from django.dispatch import receiver
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def invalidate_post_cache(sender, obj, operation, **kwargs):
        """Invalidate cache whenever a post version changes"""
        content = obj.content
        cache.delete(f"post_{content.pk}")


Update a search index
---------------------

The ``unpublished`` argument tells you whether a publish replaced existing content
or added new content:

.. code-block:: python

    from django.dispatch import receiver
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def update_search_index(sender, obj, operation, unpublished=None, **kwargs):
        if operation == constants.OPERATION_PUBLISH:
            if unpublished:
                index.update_document(obj.content)   # replaced existing content
            else:
                index.add_document(obj.content)      # brand new publication
        elif operation == constants.OPERATION_UNPUBLISH:
            index.remove_document(obj.content)


Send a notification on publish
------------------------------

.. code-block:: python

    from django.dispatch import receiver
    from django.core.mail import send_mail
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def notify_on_publish(sender, obj, operation, **kwargs):
        if operation == constants.OPERATION_PUBLISH:
            content = obj.content
            send_mail(
                subject=f"Post Published: {content.title}",
                message=f"Your post '{content.title}' has been published.",
                from_email="noreply@example.com",
                recipient_list=[obj.created_by.email],
                fail_silently=True,
            )


Log every version change
------------------------

Correlate the ``pre`` and ``post`` signals with the shared ``token``:

.. code-block:: python

    import logging
    from django.dispatch import receiver
    from djangocms_versioning.signals import pre_version_operation, post_version_operation
    from blog.models import PostContent

    logger = logging.getLogger(__name__)

    @receiver(pre_version_operation, sender=PostContent)
    def log_start(sender, obj, operation, token, **kwargs):
        logger.info("Starting %s for %s #%s", operation, sender.__name__, obj.pk,
                    extra={"token": token, "version_id": obj.pk})

    @receiver(post_version_operation, sender=PostContent)
    def log_done(sender, obj, operation, token, **kwargs):
        logger.info("Completed %s for %s #%s", operation, sender.__name__, obj.pk,
                    extra={"token": token, "version_id": obj.pk})


Handle the publish/unpublish pair in one action
-----------------------------------------------

Publishing a version automatically unpublishes the previously published one, so a
single publish produces both an ``OPERATION_UNPUBLISH`` and an ``OPERATION_PUBLISH``
signal. The ``unpublished`` and ``to_be_published`` arguments let you tell the
scenarios apart (see :ref:`the firing order <signal-execution-order>`):

.. code-block:: python

    from django.dispatch import receiver
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from cms.models import PageContent

    @receiver(post_version_operation, sender=PageContent)
    def handle_publish_scenario(sender, obj, operation,
                                unpublished=None, to_be_published=None, **kwargs):
        if operation == constants.OPERATION_PUBLISH:
            if unpublished:
                ...   # replacing an existing published version
            else:
                ...   # first publication of this content
        elif operation == constants.OPERATION_UNPUBLISH:
            if to_be_published:
                ...   # a replacement will be published — let the publish signal handle it
            else:
                ...   # content is going offline with no replacement


Replace the removed CMS page signals (django CMS 4.0+)
------------------------------------------------------

django CMS 4.0 removed its page publish/unpublish signals. Listen to the
``PageContent`` model instead:

.. code-block:: python

    from django.dispatch import receiver
    from cms.models import PageContent
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation

    @receiver(post_version_operation, sender=PageContent)
    def on_page_publish_unpublish(sender, obj, operation, **kwargs):
        page = obj.content.page
        if operation == constants.OPERATION_PUBLISH:
            ...   # page published
        elif operation == constants.OPERATION_UNPUBLISH:
            ...   # page unpublished


Tips
----

- **Keep handlers fast.** They run inside the version operation; offload slow work
  (mail, reindexing) to a task queue such as Celery.
- **Don't let a handler break the operation.** An unhandled exception can abort the
  publish. Wrap risky work in ``try/except`` and log failures instead of re-raising.
- **Be idempotent.** A handler may run more than once for the same logical change;
  make repeated runs safe.
