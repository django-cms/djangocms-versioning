from django.db import models

from cms.plugin_rendering import ContentRenderer, StructureRenderer
from cms.utils.placeholder import rescan_placeholders_for_obj

from . import versionables
from .constants import DRAFT, PUBLISHED


def prefetch_versioned_related_objects(instance, toolbar):
    instance, plugin = instance.get_plugin_instance()

    candidate_fields = [
        f for f in instance._meta.get_fields() if f.is_relation and not f.auto_created
    ]

    for field in candidate_fields:
        try:
            versionable = versionables.for_grouper(field.remote_field.model)
        except KeyError:
            continue
        if toolbar.edit_mode_active or toolbar.preview_mode_active:
            qs = versionable.content_model._base_manager.filter(
                versions__state__in=(DRAFT, PUBLISHED)
            ).order_by("versions__state")
        else:
            qs = versionable.content_model.objects.all()
        related_field = getattr(instance, field.name)
        if related_field:
            is_related_manager = isinstance(related_field, models.Manager)

            if is_related_manager:
                filter_key = '{}__in'.format(versionable.grouper_field_name)
                filter_values = related_field.get_queryset()
                filters = {filter_key: filter_values}
            else:
                filters = {versionable.grouper_field_name: related_field}
            # TODO Figure out grouping values-awareness
            # for extra fields other than hardcoded 'language'
            if "language" in versionable.extra_grouping_fields:
                filters["language"] = toolbar.request_language
            qs = qs.filter(**filters)

            # TODO refine it after understand prefetch in many2many field.
            # because if `related_field` is ManyRelatedManager, it is temporary,
            # we can't store `_prefetched_objectes_cache` to it, so I decide to store the
            # prefetched value to model instance.
            if is_related_manager:
                instance._prefetched_objects_cache = getattr(instance, '_prefetched_objects_cache', {})
                instance._prefetched_objects_cache[field.name] = qs
            else:
                related_field._prefetched_objects_cache = {versionable.grouper_field.remote_field.name: qs}


class VersionContentRenderer(ContentRenderer):
    def render_plugin(self, instance, context, placeholder=None, editable=False):
        prefetch_versioned_related_objects(instance, self.toolbar)
        return super().render_plugin(instance, context, placeholder, editable)

    def render_obj_placeholder(
        self, slot, context, inherit, nodelist=None, editable=True
    ):
        # FIXME This is an ad-hoc solution for page-specific rendering
        # code, which by default doesn't work well with versioning.
        # Remove this method once the issue is fixed.
        from cms.models import Placeholder

        current_obj = self.toolbar.get_object()

        # Not page, therefore we will use toolbar object as
        # the current object and render the placeholder
        rescan_placeholders_for_obj(current_obj)
        placeholder = Placeholder.objects.get_for_obj(current_obj).get(slot=slot)
        content = self.render_placeholder(
            placeholder,
            context=context,
            page=current_obj,
            editable=editable,
            use_cache=True,
            nodelist=None,
        )
        return content


class VersionStructureRenderer(StructureRenderer):
    def render_plugin(self, instance, page=None):
        prefetch_versioned_related_objects(instance, self.toolbar)
        return super().render_plugin(instance, page)
