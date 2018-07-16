import factory

from .blogpost.models import BlogContent, BlogPost, BlogPostVersion
from .polls.models import Poll, PollContent, PollVersion


class PollFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Poll


class PollVersionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = PollVersion


class PollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)

    class Meta:
        model = PollContent


class PollContentWithVersionFactory(PollContentFactory):

    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method as below to define version attributes:
        # PollContentWithVersionFactory(version__label='label1')
        if not create:
            # Simple build, do nothing.
            return
        PollVersionFactory(content=self, **kwargs)


class BlogPostFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = BlogPost


class BlogPostVersionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = BlogPostVersion


class BlogContentFactory(factory.django.DjangoModelFactory):
    blogpost = factory.SubFactory(BlogPostFactory)

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
