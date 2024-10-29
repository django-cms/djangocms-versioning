from functools import lru_cache

from cms import __version__ as cms_version
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
            filters = {versionable.grouper_field_name: related_field}
            # TODO Figure out grouping values-awareness
            # for extra fields other than hardcoded 'language'
            if "language" in versionable.extra_grouping_fields:
                filters["language"] = toolbar.request_language
            qs = qs.filter(**filters)
            prefetch_cache = {versionable.grouper_field.remote_field.name: qs}
            related_field._prefetched_objects_cache = prefetch_cache


class VersionContentRenderer(ContentRenderer):
    def render_plugin(self, instance, context, placeholder=None, editable=False):
        prefetch_versioned_related_objects(instance, self.toolbar)
        return super().render_plugin(instance, context, placeholder, editable)

    if cms_version in ("4.1.0", "4.1.1"):
        # Only needed for CMS 4.1.0 and 4.1.1 which have fix #7924 not merged
        # With #7924, page-specific rendering works well with versioning.
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


class CMSToolbarVersioningMixin:
    @property
    @lru_cache(16)
    def content_renderer(self):
        return VersionContentRenderer(request=self.request)

    @property
    @lru_cache(16)
    def structure_renderer(self):
        return VersionStructureRenderer(request=self.request)
