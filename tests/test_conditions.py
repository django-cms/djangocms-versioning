from cms.test_utils.testcases import CMSTestCase
from django.test import SimpleTestCase

from djangocms_versioning import constants
from djangocms_versioning.conditions import (
    BoundConditions,
    Conditions,
    ReasonedBool,
    in_state,
)
from djangocms_versioning.exceptions import ConditionFailed
from djangocms_versioning.test_utils import factories


def _passing(instance, user):
    """A condition that never fails."""


def _failing(message):
    """A condition that always fails with the given message."""
    def inner(instance, user):
        raise ConditionFailed(message)
    return inner


class ReasonedBoolTestCase(SimpleTestCase):
    def test_falsy_value_behaves_like_false(self):
        result = ReasonedBool(False, "nope")

        self.assertFalse(result)
        self.assertFalse(bool(result))
        self.assertEqual(int(result), 0)

    def test_truthy_value_behaves_like_true(self):
        result = ReasonedBool(True, "irrelevant")

        self.assertTrue(result)
        self.assertTrue(bool(result))
        self.assertEqual(int(result), 1)

    def test_reason_exposed_via_str(self):
        result = ReasonedBool(False, "the reason")

        self.assertEqual(str(result), "the reason")
        self.assertEqual(result.reason, "the reason")

    def test_reason_defaults_to_empty_string(self):
        result = ReasonedBool(False)

        self.assertEqual(result.reason, "")
        self.assertEqual(str(result), "")

    def test_non_bool_value_is_coerced(self):
        # Any truthy/falsy value is coerced to a real bool int (0/1)
        self.assertEqual(int(ReasonedBool(5, "x")), 1)
        self.assertEqual(int(ReasonedBool(0, "x")), 0)
        self.assertEqual(int(ReasonedBool([], "x")), 0)
        self.assertEqual(int(ReasonedBool(["item"], "x")), 1)

    def test_can_be_used_in_not_expression(self):
        # The whole point: `if not check.as_bool(...)` keeps working
        self.assertTrue(not ReasonedBool(False, "reason"))
        self.assertFalse(not ReasonedBool(True, "reason"))


class ConditionsAsBoolTestCase(SimpleTestCase):
    def test_returns_plain_true_when_all_conditions_pass(self):
        conditions = Conditions([_passing, _passing])

        result = conditions.as_bool(object(), object())

        self.assertIs(result, True)

    def test_returns_reasoned_bool_when_a_condition_fails(self):
        conditions = Conditions([_failing("boom")])

        result = conditions.as_bool(object(), object())

        self.assertIsInstance(result, ReasonedBool)
        self.assertFalse(result)
        self.assertEqual(str(result), "boom")

    def test_failure_reason_is_the_first_failing_condition(self):
        conditions = Conditions([
            _passing,
            _failing("first failure"),
            _failing("second failure"),
        ])

        result = conditions.as_bool(object(), object())

        self.assertEqual(str(result), "first failure")

    def test_added_conditions_still_report_reasons(self):
        # __add__ must keep returning a Conditions instance so as_bool works
        conditions = Conditions([_passing]) + [_failing("added failure")]

        self.assertIsInstance(conditions, Conditions)
        result = conditions.as_bool(object(), object())

        self.assertFalse(result)
        self.assertEqual(str(result), "added failure")


class BoundConditionsAsBoolTestCase(SimpleTestCase):
    def test_bound_conditions_propagate_reason(self):
        instance = object()
        conditions = Conditions([_failing("bound failure")])
        bound = BoundConditions(conditions, instance)

        result = bound.as_bool(object())

        self.assertIsInstance(result, ReasonedBool)
        self.assertFalse(result)
        self.assertEqual(str(result), "bound failure")

    def test_bound_conditions_pass(self):
        bound = BoundConditions(Conditions([_passing]), object())

        self.assertIs(bound.as_bool(object()), True)

    def test_descriptor_access_returns_bound_conditions(self):
        class Holder:
            checks = Conditions([_failing("from descriptor")])

        instance = Holder()

        # Accessing on the instance binds it; accessing on the class does not.
        self.assertIsInstance(instance.checks, BoundConditions)
        self.assertIsInstance(Holder.checks, Conditions)

        result = instance.checks.as_bool(object())
        self.assertEqual(str(result), "from descriptor")


class CheckConditionReasonIntegrationTestCase(CMSTestCase):
    """The failure reason of a real Version's checks reaches the caller."""

    def test_passing_check_returns_true(self):
        user = self.get_superuser()
        version = factories.PollVersionFactory(state=constants.DRAFT)

        result = version.check_publish.as_bool(user)

        self.assertIs(result, True)

    def test_failing_check_returns_state_reason(self):
        user = self.get_superuser()
        version = factories.PollVersionFactory(state=constants.ARCHIVED)

        result = version.check_publish.as_bool(user)

        self.assertFalse(result)
        self.assertEqual(str(result), "Version is not in draft state")

    def test_failing_permission_check_returns_permission_reason(self):
        # A user without permission fails the user_can_publish condition,
        # which runs before the in_state check.
        user = self.get_standard_user()
        version = factories.PollVersionFactory(state=constants.DRAFT)

        result = version.check_publish.as_bool(user)

        self.assertFalse(result)
        self.assertEqual(str(result), "You do not have publish permissions")

    def test_in_state_condition_reason_directly(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        conditions = Conditions([in_state([constants.DRAFT], "must be draft")])

        result = conditions.as_bool(version, self.get_superuser())

        self.assertFalse(result)
        self.assertEqual(str(result), "must be draft")
