# Changing breadcrumbs

To override how breadcrumbs look on the version table page, you can create a template with a path that follows this pattern:
`templates/admin/djangocms_versioning/<app_label>/<model>/versioning_breadcrumbs.html`
This will override the breadcrumbs for the model specified.

In addition to the context vars which are present in the django admin changelist view, you can also access the following in the template:
* `{{ grouper }}` - this is the grouper instance for the versions being displayed
* `{{ latest_content }}` - this is the content instance for the latest version of those displayed
* `{{ breadcrumb_opts }}` - like `{{ opts }}` (which is present in the django admin template context as standard), but for the content model
