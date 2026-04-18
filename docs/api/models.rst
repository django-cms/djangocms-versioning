Version Model API
=================

The ``Version`` model is the core model of djangocms-versioning, containing metadata about each version of your content.

Version Model Fields
--------------------

.. py:attribute:: created

    **Type**: DateTimeField (auto-set on creation, read-only)

    The date and time when the version was created.


.. py:attribute:: modified

    **Type**: DateTimeField (auto-set on modification)

    The date and time when the version was last modified.


.. py:attribute:: created_by

    **Type**: ForeignKey to AUTH_USER_MODEL

    The user who created this version. This field is required and cannot be null.


.. py:attribute:: number

    **Type**: CharField (max_length=11)

    The version number, e.g., "1", "2", "3". Used for user-friendly identification.


.. py:attribute:: content_type

    **Type**: ForeignKey to ContentType

    The Django content type of the versioned content model. Used with ``object_id`` to create a generic foreign key.


.. py:attribute:: object_id

    **Type**: PositiveIntegerField

    The primary key of the versioned content object. Used with ``content_type`` to create a generic foreign key.


.. py:attribute:: content

    **Type**: GenericForeignKey

    A convenience property that returns the actual versioned content object by combining ``content_type`` and ``object_id``.

    **Example**::

        version = Version.objects.first()
        content_object = version.content  # Returns the actual PostContent, PageContent, etc.


.. py:attribute:: state

    **Type**: FSMField (choices from VERSION_STATES)

    The version state. One of:

    - ``"draft"``: Currently editable draft version
    - ``"published"``: Currently visible to the public
    - ``"unpublished"``: Was published but is no longer public
    - ``"archived"``: Never been published, reserved for later work

    See :ref:`version-states` for more information.


.. py:attribute:: locked_by

    **Type**: ForeignKey to AUTH_USER_MODEL (nullable, defaults to None)

    The user who locked this version (if ``DJANGOCMS_VERSIONING_LOCK_VERSIONS`` is enabled).
    Only set when a version is locked. See :ref:`locking-versions` for details.


.. py:attribute:: source

    **Type**: ForeignKey to Version (self-referential, nullable)

    The version that was used as a source when creating this version. Used to track version history.
    Set to null if this is the first version or if the source has been deleted.


Version Model Methods
---------------------

.. py:method:: verbose_name()

    **Returns**: str

    Returns a human-readable string representation of the version including version number, state, and creation date.

    **Example**::

        version = Version.objects.first()
        print(version.verbose_name())  # Output: "Version #1 (draft Jan. 1, 2024, 10 a.m.)"


.. py:method:: short_name()

    **Returns**: str

    Returns a short human-readable string representation of the version including version number and state.

    **Example**::

        version = Version.objects.first()
        print(version.short_name())  # Output: "Version #1 (draft)"


.. py:method:: locked_message()

    **Returns**: str or None

    Returns a user-friendly message if the version is locked, indicating who locked it. Returns None if not locked.

    **Example**::

        if version.locked_message():
            print(f"Cannot edit: {version.locked_message()}")


Version Model State Transitions
-------------------------------

The Version model uses Django FSM (Finite State Machine) to manage state transitions. The available transitions are:

.. list-table:: Version State Transitions
   :widths: 20 20 20 40
   :header-rows: 1

   * - From State
     - To State
     - Transition Method
     - Description
   * - draft
     - published
     - ``publish()``
     - Publishes the draft, making it publicly visible
   * - published
     - unpublished
     - ``unpublish()``
     - Unpublishes a published version
   * - unpublished
     - draft
     - ``revert()``
     - Reverts to an unpublished version as a new draft
   * - archived
     - draft
     - ``revert()``
     - Reverts to an archived version as a new draft
   * - draft
     - archived
     - ``archive()``
     - Archives a draft version


Version QuerySet Methods
------------------------

The Version model provides a custom queryset with helper methods:

.. py:method:: get_for_content(content_object)

    **Parameters**:
        - ``content_object``: The versioned content instance

    **Returns**: Version instance

    Returns the Version object for the provided content object.

    **Example**::

        from djangocms_versioning.models import Version

        content = PostContent.objects.first()
        version = Version.objects.get_for_content(content)


.. py:method:: filter_by_grouper(grouper_object)

    **Parameters**:
        - ``grouper_object``: The grouper model instance

    **Returns**: QuerySet of Version objects

    Returns all Version objects for the provided grouper object, across all languages/grouping fields.

    **Example**::

        post = Post.objects.first()  # grouper
        versions = Version.objects.filter_by_grouper(post)
        for version in versions:
            print(version.verbose_name())


.. py:method:: filter_by_grouping_values(versionable, **kwargs)

    **Parameters**:
        - ``versionable``: A VersionableItem instance
        - ``**kwargs``: Grouping field values (e.g., language='en')

    **Returns**: QuerySet of Version objects

    Returns Version objects filtered by specific grouping values.

    **Example**::

        from djangocms_versioning import versionables
        from djangocms_versioning.models import Version

        versionable = versionables.for_content(PostContent)
        versions = Version.objects.filter_by_grouping_values(
            versionable,
            language='en'
        )


.. py:method:: filter_by_content_grouping_values(content)

    **Parameters**:
        - ``content``: A versioned content instance

    **Returns**: QuerySet of Version objects

    Returns Version objects for all versions of the same grouper, extracting grouping values from the provided content instance.

    **Example**::

        content = PostContent.objects.first()
        versions = Version.objects.filter_by_content_grouping_values(content)


Version Model Permissions
-------------------------

The Version model includes a custom permission:

- **delete_versionlock**: Allows a user to unlock versions (when ``DJANGOCMS_VERSIONING_LOCK_VERSIONS`` is enabled).


Version Model Manager
---------------------

.. py:attribute:: objects

    **Type**: VersionQuerySet.as_manager()

    The default manager providing access to Version objects through the custom QuerySet methods above.

    **Example**::

        all_versions = Version.objects.all()
        draft_versions = Version.objects.filter(state=DRAFT)


Accessing Version Objects
--------------------------

Published Content (Default Manager)
++++++++++++++++++++++++++++++++++++

When querying versioned content models directly, only published versions are returned:

.. code-block:: python

    # Returns only published blog posts
    posts = PostContent.objects.filter(language='en')


All Content (Admin Manager)
++++++++++++++++++++++++++++

To access all versions (draft, published, unpublished, archived) in admin views:

.. code-block:: python

    # Returns all versions of all posts
    all_posts = PostContent.admin_manager.all()

    # Filter by specific state
    from djangocms_versioning.constants import DRAFT
    draft_posts = PostContent.admin_manager.filter(versions__state=DRAFT)


Current Content
+++++++++++++++

Get the current (either draft or published) version of content:

.. code-block:: python

    # Returns draft versions if they exist, otherwise published
    current_posts = PostContent.admin_manager.current_content(language='en')

    # Equivalent to manually filtering
    from djangocms_versioning.constants import DRAFT, PUBLISHED
    current = PostContent.admin_manager.filter(
        versions__state__in=[DRAFT, PUBLISHED]
    ).distinct()


Latest Content
+++++++++++++++

Get the latest version regardless of state:

.. code-block:: python

    # Returns the latest version in this order:
    # 1. draft (if exists)
    # 2. published (if exists)
    # 3. any other version with highest pk
    latest_posts = PostContent.admin_manager.latest_content()
