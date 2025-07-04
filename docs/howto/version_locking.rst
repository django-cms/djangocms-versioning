.. _locking-versions:

****************
Locking versions
****************

Explanation
-----------
The lock versions setting is intended to modify the way djangocms-versioning works in the following way:

- A version is **locked to its author** when a draft is created.
- The lock prevents editing of the draft by anyone other than the author.
- That version becomes automatically unlocked again once it is published.
- Locks can be removed by a user with the correct permission (``delete_versionlock``)
- Unlocking an item sends an email notification to the author to which it was locked.
- Manually unlocking a version does not lock it to the unlocking user, nor does it change the author.
- The Version admin view for each versioned content-type shows lock icons and offers unlock actions

Activation
----------
In your project's ``settings.py`` add::

    DJANGOCMS_VERSIONING_LOCK_VERSIONS = True



Email notifications
------------------------
Configure email notifications to fail silently by setting::

    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True
