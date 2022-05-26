from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem, default_copy

from .models import IncorrectBlogContent


def blog_method(obj, field):
    return getattr(obj, field)


class IncorrectBlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=IncorrectBlogContent,
            grouper_field_name="blogpost",
            copy_function=default_copy,
        ),
    ]
    extended_admin_field_modifiers = [
        {IncorrectBlogContent: {"non_existent_field": blog_method}},
    ]
