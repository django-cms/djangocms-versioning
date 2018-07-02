from cms.app_base import CMSAppConfig, CMSAppExtension
from django.core.exceptions import ImproperlyConfigured



# from djangocms-versioning import make_admin_pink


class VersioningCMSExtension(CMSAppExtension):

    def configure_app(self, cms_config):
        # Do anything you need to do to each app that wants to be pink
        # Check content type setting exists
        # make_admin_pink(cms_config)
        import pdb; pdb.set_trace()
        if hasattr(cms_config, 'versioning_models'):
            app_models = getattr(cms_config, 'versioning_models')
            # self._activate_signal(app_name, app_models)
        else:
            raise ImproperlyConfigured(
                "versioning_models must be defined in cms_config.py"
            )

