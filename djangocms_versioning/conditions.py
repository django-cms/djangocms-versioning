from .conf import LOCK_VERSIONS
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


def pass_condition(version, user):
    pass


def is_not_locked(message):
    """Condition that the version is not locked. Is only effective if ``settings.DJANGOCMS_VERSIONING_LOCK_VERSIONS``
    is set to ``True``"""
    if LOCK_VERSIONS:
        def inner(version, user):
            if not version_is_unlocked_for_user(version, user):
                raise ConditionFailed(message.format(user=version.locked_by))
        return inner
    return pass_condition


def is_locked(message):
    """Condition that the version is locked. Is only effective if ``settings.DJANGOCMS_VERSIONING_LOCK_VERSIONS``
    is set to ``True``"""
    def inner(version, user):
        if not LOCK_VERSIONS or not version.locked_by:
            raise ConditionFailed(message)
    return inner


def draft_is_not_locked(message):
    if LOCK_VERSIONS:
        def inner(version, user):
            try:
                # if there's a prepopulated field on version object
                # representing a draft lock, use it
                cached_draft_version_user_id = version._draft_version_user_id
                if cached_draft_version_user_id and cached_draft_version_user_id != user.pk:
                    raise ConditionFailed(message)
            except AttributeError:
                draft_version = get_latest_draft_version(version)
                if draft_version and not version_is_unlocked_for_user(draft_version, user):
                    raise ConditionFailed(message.format(user=draft_version.locked_by))
        return inner
    return pass_condition


def draft_is_locked(message):
    if LOCK_VERSIONS:
        def inner(version, user):
            try:
                # if there's a prepopulated field on version object
                # representing a draft lock, use it
                cached_draft_version_user_id = version._draft_version_user_id
                if not cached_draft_version_user_id or cached_draft_version_user_id == user.pk:
                    raise ConditionFailed(message)
            except AttributeError:
                draft_version = get_latest_draft_version(version)
                if not draft_version or version_is_unlocked_for_user(draft_version, user):
                    raise ConditionFailed(message.format(user=draft_version.locked_by))
    else:
        def inner(version, user):
            raise ConditionFailed(message)
    return inner
