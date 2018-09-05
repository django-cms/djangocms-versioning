from django.apps import apps

from cms.plugin_rendering import ContentRenderer
from cms.utils.placeholder import rescan_placeholders_for_obj

from .constants import DRAFT, PUBLISHED


def get_versionable_for_grouper(model):
    versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
    if versioning_extension.is_grouper_model_versioned(model):
        return versioning_extension.versionables_by_grouper[model]


class VersionRenderer(ContentRenderer):

    def render_plugin(self, instance, context, placeholder=None, editable=False):
        instance, plugin = instance.get_plugin_instance()

        candidate_fields = [
            f for f in instance._meta.get_fields()
            if f.is_relation and not f.auto_created
        ]
        for field in candidate_fields:
            versionable = get_versionable_for_grouper(field.rel.model)
            if not versionable:
                continue
            if self.toolbar.edit_mode_active or self.toolbar.preview_mode_active:
                # FIXME Currently this leaves multiple content object
                # for a single grouper and is potentially dangerous
                # if content should have some unique constraint
                # (for example ('page', 'language') for PageContent).
                qs = versionable.content_model._base_manager.filter(
                    versions__state__in=(DRAFT, PUBLISHED),
                ).order_by('versions__state')
            else:
                qs = versionable.content_model.objects.all()
            qs = qs.filter(**{
                versionable.grouper_field_name: getattr(instance, field.name)
            })
            prefetch_cache = {versionable.grouper_field.remote_field.name: qs}
            related_field = getattr(instance, field.name)
            related_field._prefetched_objects_cache = prefetch_cache
        return super().render_plugin(instance, context, placeholder, editable)

    def render_obj_placeholder(self, slot, context, inherit,
                               nodelist=None, editable=True):
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
