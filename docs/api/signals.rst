Signals
=======

djangocms-versioning provides signals that allow you to react to version lifecycle events. These signals can be used for tasks like:

- Invalidating caches
- Updating external search indexes
- Triggering workflows
- Logging version changes
- Sending notifications


Available Signals
-----------------

.. py:data:: pre_version_operation

    Sent **before** a version state change occurs.

    **Signal sender**: The content model class (e.g., ``PostContent``)


.. py:data:: post_version_operation

    Sent **after** a version state change has been completed successfully.

    **Signal sender**: The content model class (e.g., ``PostContent``)


Signal Parameters
-----------------

Both signals emit the following keyword arguments:

.. list-table:: Signal Parameters
   :widths: 20 60 20
   :header-rows: 1

   * - Parameter
     - Description
     - Type
   * - ``sender``
     - The content model class (e.g., PostContent, PageContent)
     - Model class
   * - ``obj``
     - The Version instance being operated on
     - Version
   * - ``operation``
     - The type of operation being performed
     - str (see Operations below)
   * - ``token``
     - A unique token to tie pre and post signals together
     - str (UUID)
   * - ``unpublished``
     - (For publish operations) List of versions that will be unpublished
     - list of Version objects
   * - ``to_be_published``
     - (For unpublish operations) List of versions that will be published as replacements
     - list of Version objects


Version Operations
-------------------

The ``operation`` parameter can have one of these values (from ``djangocms_versioning.constants``):

.. list-table:: Version Operations
   :widths: 30 70
   :header-rows: 1

   * - Operation Constant
     - Description
   * - ``OPERATION_DRAFT``
     - A new draft version has been created (or version moved to draft state)
   * - ``OPERATION_PUBLISH``
     - A draft version has been published
   * - ``OPERATION_UNPUBLISH``
     - A published version has been unpublished
   * - ``OPERATION_ARCHIVE``
     - A draft version has been archived


Signal Token
-----------

Each signal emission includes a unique ``token`` parameter that ties related pre and post signals together. This is particularly useful when:

- Multiple signals are fired in quick succession
- You need to correlate pre and post operations
- You're implementing transactional operations

**Example**::

    signal_state = {}

    @receiver(pre_version_operation)
    def before_version_change(sender, obj, operation, token, **kwargs):
        signal_state[token] = {
            'start_time': timezone.now(),
            'operation': operation,
            'version_id': obj.pk,
        }

    @receiver(post_version_operation)
    def after_version_change(sender, obj, operation, token, **kwargs):
        state = signal_state.pop(token, {})
        duration = timezone.now() - state.get('start_time', timezone.now())
        print(f"Operation {operation} took {duration.total_seconds()}s")


Common Use Cases
----------------

Invalidating a Cache
++++++++++++++++++++

.. code-block:: python

    from django.core.cache import cache
    from django.dispatch import receiver
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def invalidate_post_cache(sender, obj, operation, **kwargs):
        """Invalidate cache whenever a post version changes"""
        content = obj.content
        cache_key = f"post_{content.pk}"
        cache.delete(cache_key)


Updating a Search Index
+++++++++++++++++++++++

.. code-block:: python

    from django.dispatch import receiver
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def update_search_index(sender, obj, operation, unpublished=None, **kwargs):
        """Update search index when posts are published/unpublished"""

        if operation == constants.OPERATION_PUBLISH:
            # New content is now public
            if unpublished:
                # This is an update of existing content
                index.update_document(obj.content)
            else:
                # This is a new publication
                index.add_document(obj.content)

        elif operation == constants.OPERATION_UNPUBLISH:
            # Content was removed from public
            index.remove_document(obj.content)


Sending Notifications
++++++++++++++++++++

.. code-block:: python

    from django.dispatch import receiver
    from django.core.mail import send_mail
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from blog.models import PostContent

    @receiver(post_version_operation, sender=PostContent)
    def notify_on_publish(sender, obj, operation, **kwargs):
        """Send email notification when post is published"""

        if operation == constants.OPERATION_PUBLISH:
            content = obj.content
            send_mail(
                subject=f"Post Published: {content.title}",
                message=f"Your post '{content.title}' has been published.",
                from_email='noreply@example.com',
                recipient_list=[obj.created_by.email],
                fail_silently=True,
            )


Logging Version Changes
++++++++++++++++++++++

.. code-block:: python

    import logging
    from django.dispatch import receiver
    from djangocms_versioning import constants
    from djangocms_versioning.signals import pre_version_operation, post_version_operation
    from blog.models import PostContent

    logger = logging.getLogger(__name__)

    @receiver(pre_version_operation, sender=PostContent)
    def log_version_change_start(sender, obj, operation, token, **kwargs):
        logger.info(
            f"Starting {operation} for {sender.__name__} #{obj.pk}",
            extra={'token': token, 'version_id': obj.pk}
        )

    @receiver(post_version_operation, sender=PostContent)
    def log_version_change_complete(sender, obj, operation, token, **kwargs):
        logger.info(
            f"Completed {operation} for {sender.__name__} #{obj.pk}",
            extra={'token': token, 'version_id': obj.pk}
        )


Handling Multiple Versions in One Action
------------------------------------------

When you publish a version, the old published version(s) are automatically unpublished. This results in multiple signals being sent. The ``unpublished`` parameter on the publish signal and ``to_be_published`` parameter on the unpublish signal help you understand what's happening:

.. code-block:: python

    from django.dispatch import receiver
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation
    from cms.models import PageContent

    @receiver(post_version_operation, sender=PageContent)
    def handle_publish_scenario(sender, obj, operation,
                                unpublished=None, to_be_published=None, **kwargs):
        """
        Handle different publish/unpublish scenarios
        """

        if operation == constants.OPERATION_PUBLISH:
            if unpublished:
                # This is replacing another published version
                print(f"Replacing {len(unpublished)} versions")
                # Update index: replace old with new
            else:
                # This is the first time this content is published
                print("First publication")
                # Update index: add new entry

        elif operation == constants.OPERATION_UNPUBLISH:
            if to_be_published:
                # Another version will be published as replacement
                print(f"{len(to_be_published)} versions will be published")
                # No action needed, let publish signal handle it
            else:
                # Content is being removed from publication entirely
                print("Content unpublished, no replacement")
                # Update index: remove entry


Listening to CMS Page Signals (DjangoCMS 4.0+)
----------------------------------------------

The CMS used to provide page publish and unpublish signals which were removed in DjangoCMS 4.0. To replicate that behavior, listen to the PageContent model:

.. code-block:: python

    from django.dispatch import receiver
    from cms.models import PageContent
    from djangocms_versioning import constants
    from djangocms_versioning.signals import post_version_operation

    @receiver(post_version_operation, sender=PageContent)
    def on_page_publish_unpublish(sender, obj, operation, **kwargs):
        """React to page publish/unpublish operations"""

        if operation == constants.OPERATION_PUBLISH:
            # Page has been published
            page = obj.content.page
            print(f"Page published: {page.get_title()}")

        elif operation == constants.OPERATION_UNPUBLISH:
            # Page has been unpublished
            page = obj.content.page
            print(f"Page unpublished: {page.get_title()}")


Signal Execution Order
----------------------

When publishing a version, the following order of events occurs:

1. ``pre_version_operation`` signal (operation=``OPERATION_PUBLISH``)
2. Old published version transitions to unpublished
3. ``post_version_operation`` signal (operation=``OPERATION_UNPUBLISH``) with ``to_be_published`` parameter
4. New version transitions to published
5. ``post_version_operation`` signal (operation=``OPERATION_PUBLISH``) with ``unpublished`` parameter

This order ensures you can handle the transition properly in your signal handlers.


Best Practices
--------------

1. **Keep signals fast**: Long-running operations in signals can block the UI. Consider using Celery for heavy operations.

2. **Handle errors gracefully**: If your signal handler raises an exception, it may break the operation:

   .. code-block:: python

       @receiver(post_version_operation, sender=PostContent)
       def my_signal_handler(sender, obj, operation, **kwargs):
           try:
               # Do something risky
               risky_operation()
           except Exception as e:
               logger.error(f"Signal handler failed: {e}", exc_info=True)
               # Don't re-raise; let the version operation complete

3. **Use tokens for debugging**: The token parameter helps correlate related operations in logs.

4. **Document your assumptions**: Make it clear which operations your handler responds to.

5. **Be idempotent**: Signal handlers may be called multiple times; design them to be safe when repeated.
