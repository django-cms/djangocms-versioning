from django.apps import apps
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from cms.toolbar.items import ButtonList
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


@toolbar_pool.register
class VersioningToolbar(CMSToolbar):

    def _get_proxy_model(self):
        """Helper method to get the proxy model class for the content
        model class
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[
            self.toolbar.obj.__class__]
        return versionable.version_model_proxy

    def _add_publish_button(self):
        """Helper method to add a publish button to the toolbar
        """
        publish_url = reverse('admin:djangocms_versioning_{model}_publish'.format(
            model=self._get_proxy_model().__name__.lower(),
        ), args=(self.toolbar.obj.pk,))
        item = ButtonList(side=self.toolbar.RIGHT)
        item.add_button(
            _('Publish'),
            url=publish_url,
            disabled=False,
        )
        self.toolbar.add_item(item)

    def post_template_populate(self):
        super(VersioningToolbar, self).post_template_populate()
        self._add_publish_button()
