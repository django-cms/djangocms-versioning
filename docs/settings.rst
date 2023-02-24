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
