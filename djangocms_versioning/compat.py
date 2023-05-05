from distutils.version import LooseVersion

import django

DJANGO_GTE_30 = LooseVersion(django.get_version()) >= LooseVersion("3.0")
