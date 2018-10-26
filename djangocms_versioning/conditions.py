from functools import partial

from .exceptions import ConditionFailed


class Conditions(list):

    def __add__(self, other):
        return Conditions(super().__add__(other))

    def __get__(self, instance, cls):
        if instance:
            return partial(self, instance)
        return self

    def __call__(self, instance, user):
        return all(func(instance, user) for func in self)

    def as_bool(self, instance, user):
        try:
            self(instance, user)
        except ConditionFailed as e:
            return False
        return True


def in_state(states, message):
    def inner(version, user):
        if version.state not in states:
            raise ConditionFailed(message)
    return inner
