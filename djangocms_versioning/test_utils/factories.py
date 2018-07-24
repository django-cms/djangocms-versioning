import factory
from factory.fuzzy import FuzzyText

from .blogpost.models import BlogContent, BlogPost, BlogPostVersion
from .polls.models import Answer, Poll, PollContent, PollVersion


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


class PollVersionFactory(factory.django.DjangoModelFactory):
    content = factory.SubFactory(PollContentFactory)

    class Meta:
        model = PollVersion


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


class BlogPostVersionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = BlogPostVersion


class BlogContentFactory(factory.django.DjangoModelFactory):
    blogpost = factory.SubFactory(BlogPostFactory)
    language = 'en'
    text = FuzzyText(length=24)

    class Meta:
        model = BlogContent


class BlogContentWithVersionFactory(BlogContentFactory):

    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # BlogContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        BlogPostVersionFactory(content=self, **kwargs)
