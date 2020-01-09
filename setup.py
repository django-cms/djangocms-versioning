from setuptools import find_packages, setup

import djangocms_versioning


INSTALL_REQUIREMENTS = [
    "Django>=1.11,<3.0",
    "django-cms",
    "django-fsm>=2.6,<2.7"
]

TEST_REQUIREMENTS = [
    "djangocms_helper",
    "pillow<=5.4.1",  # Requirement for tests to be passing in python 3.4
    "djangocms-text-ckeditor",
    "factory-boy",
    "freezegun",
    "lxml<=4.3.5",
    "bs4",
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
    url="http://github.com/divio/djangocms-versioning",
    license="BSD",
    zip_safe=False,
    tests_require=TEST_REQUIREMENTS,
    dependency_links=[
        "https://github.com/jonathan-s/django-cms/tarball/django-2.2#egg=django-cms-4.0.0",
        "https://github.com/divio/djangocms-text-ckeditor/tarball/support/4.0.x#egg=djangocms-text-ckeditor-4.0.x",
    ]
)
