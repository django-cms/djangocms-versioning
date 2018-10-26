from .exceptions import ConditionFailed


class Conditions(list):

    def __add__(self, other):
        return Conditions(super().__add__(other))

    def __get__(self, instance, cls):
        if instance:
            return BoundConditions(self, instance)
        return self

    def __call__(self, instance, user):
        return all(func(instance, user) for func in self)

    def as_bool(self, instance, user):
        try:
            self(instance, user)
        except ConditionFailed as e:
            return False
        return True


class BoundConditions:

    def __init__(self, conditions, instance):
        self.conditions = conditions
        self.instance = instance

    def __call__(self, user):
        return self.conditions(self.instance, user)

    def as_bool(self, user):
        return self.conditions.as_bool(self.instance, user)


def in_state(states, message):
    def inner(version, user):
        if version.state not in states:
            raise ConditionFailed(message)
    return inner
