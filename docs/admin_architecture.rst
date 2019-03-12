The Admin with Versioning
==========================


The content model admin
------------------------
Versioning modifies (monkeypatches) the admin for each :term:`content model <content model>`. This is because
versioning duplicates content model records every time a new version is created (since content models hold the version data
that's content type specific). Versioning therefore needs to limit the queryset in the content model admin to
include only the records for the latest versions.


The Version model admin
------------------------

Proxy models
+++++++++++++
Versioning generates a `proxy model
<https://docs.djangoproject.com/en/dev/topics/db/models/#proxy-models>`_
for each 


UI filters
+++++++++++

Versioning generates ``FakeFilter`` classes (inheriting from django's ``admin.SimpleListFilter``) for each
:term:`extra grouping field <extra grouping field>`. The purpose of these is to make the django admin display the filter
in the UI. But these ``FakeFilter`` classes don't actually do any filtering as this is actually handled by
``VersionChangeList.get_grouping_field_filters``.
