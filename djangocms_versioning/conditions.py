import typing

from django.conf import settings

from . import conf
from .exceptions import ConditionFailed
from .helpers import get_latest_draft_version, version_is_unlocked_for_user


class Conditions(list):
    def __add__(self, other: list) -> "Conditions":
        return Conditions(super().__add__(other))

    def __get__(self, instance: object, cls) -> typing.Union["Conditions", "BoundConditions"]:
        if instance:
            return BoundConditions(self, instance)
        return self

    def __call__(self, instance: object, user: settings.AUTH_USER_MODEL) -> None:
        for func in self:
            func(instance, user)

    def as_bool(self, instance: object, user: settings.AUTH_USER_MODEL) -> bool:
        try:
            self(instance, user)
        except ConditionFailed:
            return False
        return True


class BoundConditions:
    def __init__(self, conditions: Conditions, instance: object) -> None:
        self.conditions = conditions
        self.instance = instance

    def __call__(self, user) -> None:
        self.conditions(self.instance, user)

    def as_bool(self, user) -> bool:
        return self.conditions.as_bool(self.instance, user)


def in_state(states: list, message: str) -> callable:
    def inner(version, user):
        if version.state not in states:
            raise ConditionFailed(message)

    return inner


def is_not_locked(message: str) -> callable:
    """Condition that the version is not locked. Is only effective if ``settings.DJANGOCMS_VERSIONING_LOCK_VERSIONS``
    is set to ``True``"""
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            if not version_is_unlocked_for_user(version, user):
                raise ConditionFailed(message.format(user=version.locked_by))
    return inner


def draft_is_not_locked(message: str) -> callable:
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            draft_version = get_latest_draft_version(version)
            if draft_version and not version_is_unlocked_for_user(draft_version, user):
                raise ConditionFailed(message.format(user=draft_version.locked_by))
    return inner


def draft_is_locked(message: str) -> callable:
    def inner(version, user):
        if conf.LOCK_VERSIONS:
            draft_version = get_latest_draft_version(version)
            if not draft_version or version_is_unlocked_for_user(draft_version, user):
                raise ConditionFailed(message)
        else:
            raise ConditionFailed(message)
    return inner

def user_can_publish(message: str) -> callable:
    def inner(version, user):
        if not version.has_publish_permission(user):
            raise ConditionFailed(message)
    return inner


def user_can_change(message: str) -> callable:
    def inner(version, user):
        if not version.has_change_permission(user):
            raise ConditionFailed(message)
    return inner

