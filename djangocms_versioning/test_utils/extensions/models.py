from cms.extensions.models import PageContentExtension, PageExtension


class TestPageExtension(PageExtension):
    __test__ = False  # Not a test class: keep pytest from collecting it


class TestPageContentExtension(PageContentExtension):
    __test__ = False  # Not a test class: keep pytest from collecting it
