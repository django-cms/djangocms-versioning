Settings for djangocms Versioning
=================================


.. py:attribute:: DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS

    Defaults to ``False``

    This setting controls if the ``source`` field of a ``Version`` object is
    protected. It is protected by default which implies that Django will not allow a user
    to delete a version object which itself is a source for another version object.
    This implies that the corresponding content and grouper objects cannot be
    deleted either.

    This is to protect the record of how different versions have come about.

    If set to ``True`` users can delete version objects if the have the appropriate
    rights. Set this to ``True`` if you want users to be able to delete versioned
    objects and you do not need a full history of versions, e.g. for documentation
    purposes.

    The latest version (which is not a source of a newer version) can always be
    deleted (if the user has the appropriate rights).


.. py:attribute:: DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION

    Defaults to ``True`` (for django CMS <= 4.1.0) and ``False``
    (for django CMS > 4.1.0)

    This settings specifies if djangocms-versioning should register its own
    versioned CMS menu. This is necessary for CMS <= 4.1.0. For CMS > 4.1.0, the
    django CMS core comes with a version-ready menu.

    The versioned CMS menu also shows draft content in edit and preview mode.

    Using the versioned CMS menu is deprecated and it is not compatible with django
    CMS 5.1 or later.


.. py:attribute:: DJANGOCMS_VERSIONING_LOCK_VERSIONS

    Defaults to ``False``

    .. versionadded:: 2.0
       Before version 2.0 version locking was part of a separate package.

    This setting controls if draft versions are locked. If they are, only the user
    who created the draft can change the draft. See
    :ref:`Locking versions <locking-versions>` for more details.


.. py:attribute:: DJANGOCMS_VERSIONING_USERNAME_FIELD

    Defaults to ``"username"``

    Adjust this settings if your custom ``User`` model does contain a username
    field which has a different name.


.. py:attribute:: DJANGOCMS_VERSIONING_DEFAULT_USER

    Defaults to ``None``

    Creating versions require a user. For management commands (including
    migrations) either a user can be provided or this default user is
    used. If not set and no user is specified for the management command, it
    will fail.


.. py:attribute:: DJANGOCMS_VERSIONING_ON_PUBLISH_REDIRECT

    Defaults to ``"published"``

    .. versionadded:: 2.0
       Before version 2.0 the behavior was always ``"versions"``.

    This setting determines what happens after publication/unpublication of a
    content object. Three options exist:

    * ``"versions"``: The user will be redirected to a version overview of
      the current object. This is particularly useful for advanced users who
      need to keep a regular overview on the existing versions.

    * ``"published"``: The user will be redirected to the content object on
      the site. Its URL is determined by calling ``.get_absolute_url()`` on
      the content object. If does not have an absolute url or the object was
      unpublished the user is redirected to the object's preview endpoint.
      This is particularly useful if users only want to interact with versions
      if necessary.

    * ``"preview"``: The user will be redirected to the content object's
      preview endpoint.

.. py:attribute:: DJANGOCMS_VERISONING_VERBOSE_UI

    Defaults to ``True``

    For many users it is sufficient to interact with djangocms-versioning
    through a less verbose UI. If set to ``False``, djangocms-versioning will
    not display the creation date in the "manage versions" view. Also, it will
    remove its entries in the django admin overview page (index).
    "manage versions" remains accessible trough the version menu in the CMS
    toolbar.
