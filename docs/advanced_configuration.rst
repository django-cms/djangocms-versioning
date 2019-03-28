Advanced configuration
======================

For the most important configuration options see :doc:`versioning_integration`. Below are additional configuration options built into versioning.


Overriding how versioning handles core cms models
-------------------------------------------------
By default django-cms models will be registered with versioning automatically. If you do not
want that to happen set ``VERSIONING_CMS_MODELS_ENABLED`` in `settings.py` to False.
You could also set that setting to False and register the django-cms models yourself
with different options.


Adding to the context of versioning admin views
------------------------------------------------

Currently versioning supports adding context variables to the unpublish confirmation view. Wider support for adding context variables is planned, but at the moment only the unpublish confirmation view is supported. This is how one would configure this in `cms_config.py`:

.. code-block:: python

    # blog/cms_config.py
    from collections import OrderedDict
    from cms.app_base import CMSAppConfig


    def stories_about_intelligent_cats(request, version, *args, **kwargs):
        return version.content.cat_stories


     class SomeConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning_add_to_confirmation_context = {
            'unpublish': OrderedDict([('cat_stories', stories_about_intelligent_cats)]),
        }


Any context variable added to this setting will be displayed on the unpublish confirmation page automatically, but if you wish to change where on the page it displays, you will need to override the `djangocms_versioning/admin/unpublish_confirmation.html` template.


Additional options on the VersionableItem class
-------------------------------------------------
The three mandatory attributes of `VersionableItem` are described in detail on the :doc:`versioning_integration` page. Below are additional options you might want to set.


preview_url
+++++++++++
This will define the url that will be used for each version on the version list table.

.. code-block:: python

    # some_app/cms_config.py
    from django.urls import reverse
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem


    def get_preview_url(obj):
        return reverse('some_interesting_url', args=(obj.pk,))


     class SomeCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning = [
            VersionableItem(
                ....,
                preview_url=get_preview_url,
            ),
        ]


.. _extra_grouping_fields:

extra_grouping_fields
++++++++++++++++++++++
Defines one or more :term:`extra grouping fields <extra grouping field>`. This will add a UI filter to the version list table enabling filtering by that field.

.. code-block:: python

    # some_app/cms_config.py
    from django.urls import reverse
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem


     class SomeCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning = [
            VersionableItem(
                ....,
                extra_grouping_fields=["language"],
            ),
        ]

version_list_filter_lookups
++++++++++++++++++++++++++++
Must be defined if the :ref:`extra_grouping_fields` option has been set. This will let the UI filter know what values it should allow filtering by.

.. code-block:: python

    # some_app/cms_config.py
    from django.urls import reverse
    from cms.app_base import CMSAppConfig
    from cms.utils.i18n import get_language_tuple
    from djangocms_versioning.datastructures import VersionableItem


     class SomeCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning = [
            VersionableItem(
                ....,
                version_list_filter_lookups={"language": get_language_tuple},
            ),
        ]

grouper_selector_option_label
++++++++++++++++++++++++++++++

If the version table link is specified without a grouper param, a form with a dropdown of grouper objects will display. This setting defines how the labels of those groupers will display on the dropdown.


.. code-block:: python

    # some_app/cms_config.py
    from django.urls import reverse
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem


    def grouper_label(obj, language):
        return "{title} ({language})".format(title=obj.title, language=language)


     class SomeCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning = [
            VersionableItem(
                ....,
                grouper_selector_option_label=grouper_label,
            ),
        ]

content_admin_mixin
++++++++++++++++++++
Versioning modifies how the admin of the :term:`content model <content model>` works with `VersioningAdminMixin`. But you can modify this mixin with this setting.

.. code-block:: python

    # some_app/cms_config.py
    from django.urls import reverse
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem


    class SomeContentAdminMixin(VersioningAdminMixin):
        # override any standard django ModelAdmin attributes and methods
        # in this class

        def has_add_permission(self, request):
            return False


     class SomeCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        versioning = [
            VersionableItem(
                ....,
                content_admin_mixin=SomeContentAdminMixin,
            ),
        ]
