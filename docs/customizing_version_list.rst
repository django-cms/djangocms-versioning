Customizing the Version Table Admin View
=========================================


Changing breadcrumbs
----------------------

To override how breadcrumbs look on the version table page, you can create a template with a path that follows this pattern:

``templates/admin/djangocms_versioning/<app_label>/<model>/versioning_breadcrumbs.html``

This will override the breadcrumbs for the model specified.

In addition to the context vars which are present as standard in the django admin changelist view, you can also access the following in the template:

- ``{{ grouper }}`` - this is the grouper instance for the versions being displayed
- ``{{ latest_content }}`` - this is the content instance for the latest version of those displayed
- ``{{ breadcrumb_opts }}`` - like ``{{ opts }}`` (which is present in the django admin template context as standard), but for the content model


Changing the preview url
-------------------------

You can configure versioning to use a different preview url for versions in the table. See :ref:`preview_url` for details.


Adding additional UI filters
-----------------------------

If you need to be able to filter the versions by fields on the :term:`content model <content model>` (for example by language), the best way of doing so is to use the configuration options :ref:`extra_grouping_fields` and :ref:`version_list_filter_lookups`.
