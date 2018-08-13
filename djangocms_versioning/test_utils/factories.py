from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

import factory
from factory.fuzzy import FuzzyText

from djangocms_versioning.models import Version

from .blogpost.models import BlogContent, BlogPost
from .polls.models import Answer, Poll, PollContent


class UserFactory(factory.django.DjangoModelFactory):
    username = FuzzyText(length=12)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(
        lambda u: "%s.%s@example.com" % (u.first_name.lower(), u.last_name.lower()))

    class Meta:
        model = User


class AbstractVersionFactory(factory.DjangoModelFactory):
    object_id = factory.SelfAttribute('content.id')
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content))
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        exclude = ['content']
        abstract = True


class PollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = Poll


class PollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    language = 'en'
    text = FuzzyText(length=24)

    class Meta:
        model = PollContent


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
