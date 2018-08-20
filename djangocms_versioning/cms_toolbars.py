from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from cms.toolbar.items import ButtonList
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool

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
        return versioning_extension.is_content_model_versioned(
            self.toolbar.obj.__class__)

    def _get_proxy_model(self):
        """Helper method to get the proxy model class for the content
        model class
        """
        return self._get_versionable().version_model_proxy

    def _add_publish_button(self):
        """Helper method to add a publish button to the toolbar
        """
        # Only add the publish button if the content type is registered
        # with versioning
        if not self._is_versioned():
            return
        # Add the publish button if in edit mode
        if self.toolbar.edit_mode_active:
            item = ButtonList(side=self.toolbar.RIGHT)
            proxy_model = self._get_proxy_model()
            version = Version.objects.get_for_content(self.toolbar.obj)
            publish_url = reverse('admin:{app}_{model}_publish'.format(
                app=proxy_model._meta.app_label,
                model=proxy_model.__name__.lower(),
            ), args=(version.pk,))
            item.add_button(
                _('Publish'),
                url=publish_url,
                disabled=False,
                extra_classes=['cms-btn-action'],
            )
            self.toolbar.add_item(item)

    def _add_edit_button(self):
        """Helper method to add an edit button to the toolbar
        """
        # Only add the edit button if the content type is registered
        # with versioning
        if not self._is_versioned():
            return
        # Add the edit button if in preview mode
        if self.toolbar.content_mode_active:
            item = ButtonList(side=self.toolbar.RIGHT)
            proxy_model = self._get_proxy_model()
            version = Version.objects.get_for_content(self.toolbar.obj)
            edit_url = reverse('admin:{app}_{model}_edit_redirect'.format(
                app=proxy_model._meta.app_label,
                model=proxy_model.__name__.lower(),
            ), args=(version.pk,))
            item.add_button(
                _('Edit'),
                url=edit_url,
                disabled=False,
                extra_classes=['cms-btn-action'],
            )
            self.toolbar.add_item(item)

    def post_template_populate(self):
        super(VersioningToolbar, self).post_template_populate()
        self._add_edit_button()
        self._add_publish_button()
