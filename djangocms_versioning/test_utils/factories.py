from django.contrib.contenttypes.models import ContentType

import factory
from factory.fuzzy import FuzzyText

from django.contrib.auth.models import User
from djangocms_versioning.models import Version

from .blogpost.models import BlogContent, BlogPost
from .polls.models import \
    Answer, Poll, PollArticle, PollContent, Category, PollExtension, Survey, Tag


class AbstractVersionFactory(factory.DjangoModelFactory):
    object_id = factory.SelfAttribute('content.id')
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content))

    class Meta:
        exclude = ['content']
        abstract = True


class PollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = Poll


class PollExtensionFactory(factory.django.DjangoModelFactory):
    help_text = FuzzyText(length=24)

    class Meta:
        model = PollExtension


class PollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    language = 'en'
    text = FuzzyText(length=24)

    class Meta:
        model = PollContent

    @factory.post_generation
    def categories(self, create, categories, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if categories:
            self.categories.add(*categories)


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
        lambda o, n: 'Poll %s - Answer %d' % (o.poll_content.poll.name, n))

    class Meta:
        model = Answer


class CategoryFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=12)

    class Meta:
        model = Category


class SurveyFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=12)

    class Meta:
        model = Survey


class PollArticleFactory(factory.django.DjangoModelFactory):
    poll_content = factory.SubFactory(PollContentFactory)
    text = FuzzyText(length=60)

    class Meta:
        model = PollArticle


class TagFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=5)

    class Meta:
        model = Tag


class BlogPostFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = BlogPost


class BlogContentFactory(factory.django.DjangoModelFactory):
    blogpost = factory.SubFactory(BlogPostFactory)
    language = 'en'
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


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.LazyAttribute(lambda u: u.first_name.lower())
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(
        lambda u: "%s.%s@example.com" % (u.first_name.lower(), u.last_name.lower()))

    class Meta:
        model = User
