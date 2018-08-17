from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from cms.toolbar.items import ButtonList
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool

from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version


@toolbar_pool.register
class VersioningToolbar(CMSToolbar):

    def _get_versionable(self):
        """Helper method to get the versionable for the content type
        of the version
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        return versioning_extension.versionables_by_content[
            self.toolbar.obj.__class__]

    def _is_versioned(self):
        """Helper method to check if the model has been registered for
        versioning
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        return versioning_extension.is_content_model_versioned(self.toolbar.obj.__class__)

    def _get_proxy_model(self):
        """Helper method to get the proxy model class for the content
        model class
        """
        return self._get_versionable().version_model_proxy

    def _add_publish_button(self, item):
        """Helper method to add a publish button to the toolbar
        """
        # Only add the publish button if the content type is registered
        # with versioning
        if not self._is_versioned():
            return
        # Only add the publish button if the version is a draft
        content_type = ContentType.objects.get_for_model(self.toolbar.obj)
        version = Version.objects.get(
            content_type=content_type, object_id=self.toolbar.obj.pk)
        if version.state != DRAFT:
            return
        # Add the publish button in all other cases
        proxy_model = self._get_proxy_model()
        publish_url = reverse('admin:{app}_{model}_publish'.format(
            app=proxy_model._meta.app_label,
            model=proxy_model.__name__.lower(),
        ), args=(self.toolbar.obj.pk,))
        item.add_button(
            _('Publish'),
            url=publish_url,
            disabled=False,
        )

    def post_template_populate(self):
        super(VersioningToolbar, self).post_template_populate()
        # Create a button area on the toolbar
        item = ButtonList(side=self.toolbar.RIGHT)
        self.toolbar.add_item(item)
        # Add buttons
        self._add_publish_button(item)
