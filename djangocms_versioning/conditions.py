from . import conf
from .exceptions import ConditionFailed
from .helpers import get_latest_draft_version, version_is_unlocked_for_user


class Conditions(list):
    def __add__(self, other):
        return Conditions(super().__add__(other))

    def __get__(self, instance, cls):
        if instance:
            return BoundConditions(self, instance)
        return self

    def __call__(self, instance, user):
        for func in self:
            func(instance, user)

    def as_bool(self, instance, user):
        try:
            self(instance, user)
        except ConditionFailed:
            return False
        return True


class BoundConditions:
    def __init__(self, conditions, instance):
        self.conditions = conditions
        self.instance = instance

    def __call__(self, user):
        self.conditions(self.instance, user)

    def as_bool(self, user):
        return self.conditions.as_bool(self.instance, user)


def in_state(states, message):
    def inner(version, user):
        if version.state not in states:
            raise ConditionFailed(message)

    return inner


def is_not_locked(message):
    """Condition that the version is not locked. Is only effective if ``settings.DJANGOCMS_VERSIONING_LOCK_VERSIONS``
    is set to ``True``"""
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            if not version_is_unlocked_for_user(version, user):
                raise ConditionFailed(message.format(user=version.locked_by))
    return inner


def is_locked(message):
    """Condition that the version is locked. Is only effective if ``settings.DJANGOCMS_VERSIONING_LOCK_VERSIONS``
    is set to ``True``"""
    def inner(version, user):
        if not conf.LOCK_VERSIONS or not version.locked_by:
            raise ConditionFailed(message)
    return inner


def draft_is_not_locked(message):
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            draft_version = get_latest_draft_version(version)
            if draft_version and not version_is_unlocked_for_user(draft_version, user):
                raise ConditionFailed(message.format(user=draft_version.locked_by))
    return inner


def draft_is_locked(message):
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            draft_version = get_latest_draft_version(version)
            if not draft_version or version_is_unlocked_for_user(draft_version, user):
                raise ConditionFailed(message)
        else:
            raise ConditionFailed(message)
    return inner
