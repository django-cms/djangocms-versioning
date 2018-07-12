import factory

from .polls.models import Poll, PollContent, PollVersion


class PollFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Poll


class PollVersionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = PollVersion


class PollContentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = PollContent

    @factory.post_generation
    def version(self, create, extracted, **kwargs):
        # NOTE: Use this method like in this example:
        # PollContentFactory(poll=poll, version__label='label1')
        # where label is a field of the PollVersion object associated
        # with the PollContent object being created
        if not create:
            # Simple build, do nothing.
            return

        PollVersion(content=self, **kwargs)
