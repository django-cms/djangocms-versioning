import string

import factory
from cms import constants
from cms.models import Page, PageContent, PageUrl, Placeholder

try:
    from cms.models import TreeNode
except ImportError:
    TreeNode = None
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from djangocms_text_ckeditor.models import Text
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from ..models import Version
from .blogpost.models import BlogContent, BlogPost
from .extended_polls.models import PollPageContentExtension
from .extensions.models import TestPageContentExtension
from .incorrectly_configured_blogpost.models import (
    IncorrectBlogContent,
    IncorrectBlogPost,
)
from .polls.models import Answer, Poll, PollContent
from .unversioned_editable_app.models import FancyPoll


class UserFactory(factory.django.DjangoModelFactory):
    username = FuzzyText(length=12)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda u: f"{u.first_name.lower()}.{u.last_name.lower()}@example.com"
    )

    class Meta:
        model = User

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with our custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_user(*args, **kwargs)


class AbstractVersionFactory(factory.django.DjangoModelFactory):
    object_id = factory.SelfAttribute("content.id")
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content)
    )
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        exclude = ["content"]
        abstract = True


class AbstractContentFactory(factory.django.DjangoModelFactory):
    @classmethod
    def _get_manager(cls, model_class):
        return model_class._base_manager


class PollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = Poll


class PollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    text = FuzzyText(length=24)

    class Meta:
        model = PollContent

    @classmethod
    def _get_manager(cls, model_class):
        return model_class._base_manager


class PollVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(PollContentFactory)

    class Meta:
        model = Version


class PollContentWithVersionFactory(PollContentFactory):
    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # PollContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        PollVersionFactory(content=self, **kwargs)


class AnswerFactory(factory.django.DjangoModelFactory):
    poll_content = factory.SubFactory(PollContentFactory)
    text = factory.LazyAttributeSequence(
        lambda o, n: f"Poll {o.poll_content.poll.name} - Answer {n}"
    )

    class Meta:
        model = Answer


class BlogPostFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = BlogPost


class BlogContentFactory(AbstractContentFactory):
    blogpost = factory.SubFactory(BlogPostFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    text = FuzzyText(length=24)

    class Meta:
        model = BlogContent


class BlogPostVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(BlogContentFactory)

    class Meta:
        model = Version


class BlogContentWithVersionFactory(BlogContentFactory):
    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # BlogContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        BlogPostVersionFactory(content=self, **kwargs)


class IncorrectBlogPostFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = IncorrectBlogPost


class IncorrectBlogContentFactory(AbstractContentFactory):
    blogpost = factory.SubFactory(IncorrectBlogPostFactory)
    text = FuzzyText(length=24)

    class Meta:
        model = IncorrectBlogContent


class IncorrectBlogPostVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(IncorrectBlogContentFactory)

    class Meta:
        model = Version


class IncorrectBlogContentWithVersionFactory(IncorrectBlogContentFactory):
    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        if not create:
            return
        IncorrectBlogPostVersionFactory(content=self, **kwargs)


if TreeNode:
    class TreeNodeFactory(factory.django.DjangoModelFactory):
        site = factory.fuzzy.FuzzyChoice(Site.objects.all())
        depth = 0
        # NOTE: Generating path this way is probably not a good way of
        # doing it, but seems to work for our present tests which only
        # really need a tree node to exist and not throw unique constraint
        # errors on this field. If the data in this model starts mattering
        # in our tests then something more will need to be done here.
        path = FuzzyText(length=8, chars=string.digits)

        class Meta:
            model = TreeNode


class PageUrlFactory(factory.django.DjangoModelFactory):
    slug = ""
    path = ""
    managed = False
    language = "en"

    class Meta:
        model = PageUrl


class PageFactory(factory.django.DjangoModelFactory):
    if TreeNode:
        node = factory.SubFactory(TreeNodeFactory)
    else:
        site = factory.fuzzy.FuzzyChoice(Site.objects.all())
        depth = 0
        path = FuzzyText(length=8, chars=string.digits)

    class Meta:
        model = Page


class PageContentFactory(AbstractContentFactory):
    page = factory.SubFactory(PageFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    title = FuzzyText(length=12)
    page_title = FuzzyText(length=12)
    menu_title = FuzzyText(length=12)
    meta_description = FuzzyText(length=12)
    redirect = FuzzyText(length=12)
    created_by = FuzzyText(length=12)
    changed_by = FuzzyText(length=12)
    in_navigation = FuzzyChoice([True, False])
    soft_root = FuzzyChoice([True, False])
    limit_visibility_in_menu = constants.VISIBILITY_USERS
    template = "page.html"
    xframe_options = FuzzyInteger(0, 3)

    class Meta:
        model = PageContent


class PageVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(PageContentFactory)

    class Meta:
        model = Version


class PageContentWithVersionFactory(PageContentFactory):
    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # PageContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        PageVersionFactory(content=self, **kwargs)


class PlaceholderFactory(factory.django.DjangoModelFactory):
    default_width = FuzzyInteger(0, 25)
    slot = FuzzyText(length=2, chars=string.digits)
    # NOTE: When using this factory you will probably want to set
    # the source field manually

    class Meta:
        model = Placeholder


def get_plugin_position(plugin):
    """Helper function to correctly calculate the plugin position.
    Use this in plugin factory classes
    """
    offset = plugin.placeholder.get_last_plugin_position(plugin.language) or 0
    return offset + 1


def get_plugin_language(plugin):
    """Helper function to get the language from a plugin's relationships.
    Use this in plugin factory classes
    """
    if plugin.placeholder.source is not None:
        return plugin.placeholder.source.language
    # NOTE: If plugin.placeholder.source is None then language will
    # also be None unless set manually


class TextPluginFactory(factory.django.DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "TextPlugin"
    body = factory.fuzzy.FuzzyText(length=50)

    class Meta:
        model = Text


class FancyPollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=24)

    class Meta:
        model = FancyPoll


class PollTitleExtensionFactory(factory.django.DjangoModelFactory):
    extended_object = factory.SubFactory(PageContentFactory)
    votes = FuzzyInteger(0, 100)

    class Meta:
        model = PollPageContentExtension


class TestTitleExtensionFactory(factory.django.DjangoModelFactory):
    extended_object = factory.SubFactory(PageContentFactory)

    class Meta:
        model = TestPageContentExtension
