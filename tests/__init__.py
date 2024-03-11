import django

from cms.test_utils.testcases import CMSTestCase


if django.VERSION < (4, 2):  # TODO: remove when dropping support for Django < 4.2
    CMSTestCase.assertQuerySetEqual = CMSTestCase.assertQuerysetEqual
