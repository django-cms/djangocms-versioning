HELPER_SETTINGS = {
    "SECRET_KEY": "djangocms-versioning-test-suite",
    "USE_TZ": False,
    "TIME_ZONE": "America/Chicago",
    "INSTALLED_APPS": [
        "djangocms_text_ckeditor",
        "djangocms_versioning",
        "djangocms_versioning.test_utils.extensions",
        "djangocms_versioning.test_utils.polls",
        "djangocms_versioning.test_utils.blogpost",
        "djangocms_versioning.test_utils.text",
        "djangocms_versioning.test_utils.people",
        "djangocms_versioning.test_utils.incorrectly_configured_blogpost",
        "djangocms_versioning.test_utils.unversioned_editable_app",
        "djangocms_versioning.test_utils.extended_polls",
    ],
    "CMS_PERMISSION": True,
    "LANGUAGES": (
        ("en", "English"),
        ("de", "German"),
        ("fr", "French"),
        ("it", "Italiano"),
    ),
    "CMS_LANGUAGES": {
        1: [
            {"code": "en", "name": "English", "fallbacks": ["de", "fr"]},
            {
                "code": "de",
                "name": "Deutsche",
                "fallbacks": ["en"],  # FOR TESTING DO NOT ADD 'fr' HERE
            },
            {
                "code": "fr",
                "name": "Française",
                "fallbacks": ["en"],  # FOR TESTING DO NOT ADD 'de' HERE
            },
            {
                "code": "it",
                "name": "Italiano",
                "fallbacks": ["fr"],  # FOR TESTING, LEAVE AS ONLY 'fr'
            },
        ]
    },
    "PARLER_ENABLE_CACHING": False,
    "LANGUAGE_CODE": "en",
    "DEFAULT_AUTO_FIELD": "django.db.models.AutoField",
    "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION": True,
    "CMS_CONFIRM_VERSION4": True,
}


def run():
    from app_helper import runner

    runner.cms("djangocms_versioning", extra_args=[])


if __name__ == "__main__":
    run()
