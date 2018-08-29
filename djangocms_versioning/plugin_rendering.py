from django.apps import apps

from cms.plugin_rendering import ContentRenderer


def is_grouper_model(model):
    versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
    return versioning_extension.is_grouper_model_versioned(model)


class VersionRenderer(ContentRenderer):

    def render_plugin(self, instance, context, placeholder=None, editable=False):
        import pdb;pdb.set_trace()
        candidate_fields = [
            f for f in instance._meta.get_fields()
            if f.is_relation and not f.auto_created
        ]
        for field in candidate_fields:
            if not is_grouper_model(field.rel.model):
                continue
            prefetch_cache = {}
            related_field = getattr(instance, field.name)
            related_field._prefetched_objects_cache = prefetch_cache
        super().render_plugin(instance, context, placeholder, editable)
