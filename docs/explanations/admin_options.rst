.. _alternative_admin:

The Admin with Versioning
=========================

Versioning in django CMS provides powerful tools to manage content and grouper models in the admin interface.
This chapter explains the default patterns and customization options for integrating versioning into your admin
classes.

Proxy models of :class:`djangocms_versioning.models.Version` are generated for each registered content model,
allowing customization of the version table by model.


Default Pattern
---------------

The default pattern is to set the ``grouper_admin_mixin`` property to ``"__default__"``, which applies the
:class:`~djangocms_versioning.admin.DefaultGrouperVersioningAdminMixin` to the grouper model admin. This mixin
ensures that state indicators and admin list actions are displayed consistently.

Admin Options Overview
-----------------------

.. list-table:: Overview on versioning admin options: Grouper models
   :widths: 25 75
   :header-rows: 1

   * - Versioning state
     - Grouper Model Admin
   * - **Default**: Indicators, drop down menu
     - .. code-block:: python

            class GrouperAdmin(
                DefaultGrouperVersioningAdminMixin,
                GrouperModelAdmin
            ):
                list_display = ...
   * - Indicators, drop down menu (fix the current default)
     - .. code-block:: python

            class GrouperAdmin(
                ExtendedGrouperVersionAdminMixin,
                StateIndicatorMixin,
                GrouperModelAdmin
            ):
                list_display = ...
   * - Text, no interaction
     - .. code-block:: python

            class GrouperAdmin(
                ExtendedGrouperVersionAdminMixin,
                GrouperModelAdmin
            ):
                list_display = ...

.. list-table:: Overview on versioning admin options: Content models
   :widths: 25 75
   :header-rows: 1

   * - Versioning state
     - **Content Model Admin**
   * - Text, no interaction
     - .. code-block:: python

            class ContentAdmin(
                ExtendedVersionAdminMixin,
                admin.ModelAdmin
            )
   * - Indicators, drop down menu
     - .. code-block:: python

            class ContentAdmin(
                ExtendedIndicatorVersionAdminMixin,
                admin.ModelAdmin,
            )

Adding Versioning to Content Model Admins
-----------------------------------------

The :term:`ExtendedVersionAdminMixin` provides fields and actions related to versioning, such as:

* Author
* Modified date
* Versioning state
* Preview action
* Edit action
* Version list action

Example:

.. code-block:: python

    class PostContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
        list_display = ["title"]

The :term:`ExtendedVersionAdminMixin` also has functionality to alter fields from other apps. By adding the :term:`extended_admin_field_modifiers` to a given app's :term:`cms_config`,
in the form of a dictionary of {model_name: {field: method}}, the admin for the model will alter the field using the method provided.

.. code-block:: python

    # cms_config.py
    def post_modifier(obj, field):
        return obj.get(field) + " extra field text!"

    class PostCMSConfig(CMSAppConfig):
        # Other versioning configurations...
        admin_field_modifiers = [
            {PostContent: {"title": post_modifier}},
        ]

Given the code sample above, "This is how we add" would be displayed as
"this is how we add extra field text!" in the changelist of PostAdmin.

Adding State Indicators
-------------------------

djangocms-versioning provides status indicators for django CMS' content models, you may know them from the page tree in django-cms:

.. image:: /static/Status-indicators.png
    :width: 50%

You can use these on your content model's changelist view admin by adding the following mixin to the model's Admin class:

.. code-block:: python

    class MyContentModelAdmin(StateIndicatorMixin, admin.ModelAdmin):
        list_display = [..., "state_indicator", ...]

.. note::

    For grouper models, ensure that the admin instance defines properties for each extra grouping field (e.g., ``self.language``).
    If you derive your admin class from :class:`~cms.admin.utils.GrouperModelAdmin`, this behavior is automatically handled.

    Otherwise, this is typically set in the ``get_changelist_instance`` method, e.g., by getting the language from the request. The page
    tree, for example, keeps its extra grouping field (language) as a get parameter to avoid mixing language of the user interface and
    language that is changed.

    .. code-block:: python

        def get_changelist_instance(self, request):
            """Set language property and remove language from changelist_filter_params"""
            if request.method == "GET":
                request.GET = request.GET.copy()
                for field in versionables.for_grouper(self.model).extra_grouping_fields:
                    value = request.GET.pop(field, [None])[0]
                    # Validation is recommended: Add clean_language etc. to your Admin class!
                    if hasattr(self, f"clean_{field}"):
                        value = getattr(self, f"clean_{field}")(value):
                    setattr(self, field) = value
                # Grouping field-specific cache needs to be cleared when they are changed
                self._content_cache = {}
            instance = super().get_changelist_instance(request)
            # Remove grouping fields from filters
            if request.method == "GET":
                for field in versionables.for_grouper(self.model).extra_grouping_fields:
                    if field in instance.params:
                        del instance.params[field]
            return instance


Combining Status Indicators and Versioning
------------------------------------------

To combine both status indicators and versioning fields, use the :class:`~djangocms_versioning.admin.ExtendedIndicatorVersionAdminMixin`:

.. code-block:: python

    class MyContentModelAdmin(ExtendedIndicatorVersionAdminMixin, admin.ModelAdmin):
        ...

The versioning state and version list action are replaced by the status indicator and its context menu, respectively.

Add additional actions by overwriting the ``self.get_list_actions()`` method and calling ``super()``.

Adding Versioning to Grouper Model Admins
-----------------------------------------

For grouper models, use the :class:`~djangocms_versioning.admin.ExtendedGrouperVersionAdminMixin` to add versioning fields:

.. code-block:: python

    class PostAdmin(ExtendedGrouperVersionAdminMixin, GrouperModelAdmin):
        list_display = ["title", "get_author", "get_modified_date", "get_versioning_state"]

To also add state indicators, include the :class:`~djangocms_versioning.admin.StateIndicatorMixin`:

.. code-block:: python

    class PostAdmin(ExtendedGrouperVersionAdminMixin, StateIndicatorMixin, GrouperModelAdmin):
        list_display = ["title", "get_author", "get_modified_date", "state_indicator"]
