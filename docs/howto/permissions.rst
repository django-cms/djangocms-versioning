#####################################
 Permissions in djangocms-versioning
#####################################

This documentation covers the permissions system introduced for
publishing and unpublishing content in djangocms-versioning. This system
allows for fine-grained control over who can publish and unpublish or otherwise
manage versions of content.

***************************
 Understanding Permissions
***************************

Permissions are set at the content object level, allowing for detailed
access control based on the user's roles and permissions. The system
checks for specific methods within the **content object**, e.g.
``PageContent`` to determine if a user has the necessary permissions.

-  **Specific publish permission** (only for publish/unpublish action):
   To check if a user has the
   permission to publish content, the system looks for a method named
   ``has_publish_permission`` on the content object. If this method is
   present, it will be called to determine whether the user is allowed
   to publish the content.

   Example:

   .. code:: python

      def has_publish_permission(self, user):
          if user.is_superuser:
              # Superusers typically have permission to publish
              return True
          # Custom logic to determine if the user can publish
          return user_has_permission

-  **Change Permission** (and first fallback for ``has_publish_permission``):
   If the content object has a
   method named ``has_change_permission``, this method will be called to
   assess if a user has the permission to change the content. This is a
   general permission check that is not specific to publishing or
   unpublishing actions.

   Example:

   .. code:: python

      def has_change_permission(self, user):
          if user.is_superuser:
              # Superusers typically have permission to publish
              return True
          # Custom logic to determine if the user can change the content
          return user_has_permission

-  **First Fallback Placeholder Change Permission**: For content
   objects that involve placeholders, such as PageContent objects, a
   method named ``has_placeholder_change_permission`` is checked. This
   method should determine if the user has the permission to change
   placeholders within the content.

   Example:

   .. code:: python

      def has_placeholder_change_permission(self, user):
          if user.is_superuser:
              # Superusers typically have permission to publish
              return True
          # Custom logic to determine if the user can change placeholders
          return user_has_permission

-  **Last resort Django permissions:** If none of the above methods are
   present on the content object, the system falls back to checking if
   the user has a generic Django permission to change ``Version``
   objects. This ensures that there is always a permission check in
   place, even if specific methods are not implemented for the content
   object. By default, the Django permissions are set on a user or group
   level and include all instances of the content object.

   .. note::

      It is highly recommended to implement the specific permission
      methods on your content objects for more granular control over
      user actions.

************
 Conclusion
************

The permissions system introduced in djangocms-versioning for publishing
and unpublishing content provides a flexible and powerful way to manage
access to content. By defining custom permission logic within your
content objects, you can ensure that only authorized users are able to
perform these actions.
