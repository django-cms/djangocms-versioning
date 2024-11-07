from setuptools import find_packages, setup

import djangocms_versioning

INSTALL_REQUIREMENTS = [
    "Django>=3.2",
    "django-cms>=4.1.1",
    "django-fsm<3"
]

setup(
    name="djangocms-versioning",
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_versioning.__version__,
    description=djangocms_versioning.__doc__,
    long_description=open("README.rst").read(),
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
    install_requires=INSTALL_REQUIREMENTS,
    author="Divio AG",
    test_suite="test_settings.run",
    author_email="info@divio.ch",
    maintainer="Django CMS Association and contributors",
    maintainer_email="info@django-cms.org",
    url="https://github.com/django-cms/djangocms-versioning",
    license="BSD",
)
