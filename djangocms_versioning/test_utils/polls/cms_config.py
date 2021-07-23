from collections import OrderedDict

from cms.app_base import CMSAppConfig
from cms.utils.i18n import get_language_tuple

from djangocms_versioning.datastructures import VersionableItem, default_copy

from .models import PollContent


def unpublish_warning(request, version, *args, **kwargs):
    return "<b>Warning: Polls don't like to be unpublished!</b>"


class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            extra_grouping_fields=["language"],
            version_list_filter_lookups={"language": get_language_tuple},
            copy_function=default_copy,
            preview_url=PollContent.get_preview_url,
            admin_list_display_fields={"pollcontent": ["text"]},
        )
    ]
    versioning_add_to_confirmation_context = {
        "unpublish": OrderedDict([("warning", unpublish_warning)])
    }
