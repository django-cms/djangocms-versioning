from cms.extensions.extension_pool import ExtensionPool
from cms.models.titlemodels import PageContent


def _copy_title_extensions(self, source_page, target_page, language, clone=False):
    source_title = source_page.pagecontent_set.get(language=language)
    if target_page:
        # the line below has been modified to accomodate versioning.
        target_title = PageContent._original_manager.filter(
            page=target_page, language=language
        )
    else:
        target_title = source_title.publisher_public
    for extension in self.title_extensions:
        for instance in extension.objects.filter(extended_object=source_title):
            if clone:
                instance.copy(target_title, language)
            else:
                instance.copy_to_public(target_title, language)

ExtensionPool._copy_title_extensions = _copy_title_extensions
