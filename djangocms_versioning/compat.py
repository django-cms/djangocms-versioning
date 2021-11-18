from distutils.version import LooseVersion

import django


DJANGO_GTE_21 = LooseVersion(django.get_version()) >= LooseVersion("2.1")
DJANGO_GTE_30 = LooseVersion(django.get_version()) >= LooseVersion("3.0")
