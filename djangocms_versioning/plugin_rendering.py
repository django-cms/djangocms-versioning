from django.apps import apps

from cms.plugin_rendering import ContentRenderer

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
                qs = versionable.content_model._base_manager.filter(
                    versions__state__in=(DRAFT, PUBLISHED),
                ).order_by('versions__state')
            else:
                qs = versionable.content_model.objects.all()
            qs = qs.filter(
                **{versionable.grouper_field_name: getattr(instance, field.name)},
            )
            prefetch_cache = {versionable.grouper_field.remote_field.name: qs}
            related_field = getattr(instance, field.name)
            related_field._prefetched_objects_cache = prefetch_cache
        return super().render_plugin(instance, context, placeholder, editable)
