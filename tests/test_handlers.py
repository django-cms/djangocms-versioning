from datetime import datetime

from cms.api import add_plugin
from cms.models import Placeholder, UserSettings
from cms.test_utils.testcases import CMSTestCase
from freezegun import freeze_time

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories


class HandlersTestCase(CMSTestCase):
    def test_modified_date(self):
        pv = factories.PollVersionFactory()
        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            pv.content.save()
        pv = Version.objects.get(pk=pv.pk)
        self.assertEqual(pv.modified, dt)

    def test_add_plugin(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        placeholder.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI
        poll = factories.PollFactory()
        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_add_plugin_uri(
                placeholder=placeholder,
                plugin_type="PollPlugin",
                language=version.content.language,
            )
            data = {"poll": poll.pk}

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)
        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_change_plugin(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()

        plugin = add_plugin(
            placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_change_plugin_uri(plugin)
            data = {"poll": poll.pk}

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_clear_placeholder(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        placeholder.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_clear_placeholder_url(placeholder)

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, {"test": 0})
                self.assertEqual(response.status_code, 302)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_delete_plugin(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()

        plugin = add_plugin(
            placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_delete_plugin_uri(plugin)
            data = {"poll": poll.pk}

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 302)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_add_plugins_from_placeholder(self):
        version = factories.PageVersionFactory()
        source_placeholder = factories.PlaceholderFactory(source=version.content)
        target_placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()

        plugin = add_plugin(
            source_placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_copy_plugin_uri(plugin)
            data = {
                "source_language": version.content.language,
                "source_placeholder_id": source_placeholder.pk,
                "target_language": version.content.language,
                "target_placeholder_id": target_placeholder.pk,
            }

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_paste_placeholder(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()
        user_settings = UserSettings.objects.create(
            language=version.content.language,
            user=self.get_superuser(),
            clipboard=Placeholder.objects.create(slot="clipboard"),
        )

        placeholder_plugin = add_plugin(
            user_settings.clipboard, "PlaceholderPlugin", version.content.language
        )
        plugin = add_plugin(
            placeholder_plugin.placeholder_ref, "PollPlugin", version.content.language, poll=poll
        )

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_move_plugin_uri(plugin)
            data = {
                "plugin_id": placeholder_plugin.pk,
                "placeholder_id": placeholder.pk,
                "target_language": version.content.language,
                "move_a_copy": "true",
                "target_position": 1,
            }

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_paste_plugin(self):
        version = factories.PageVersionFactory()
        source_placeholder = factories.PlaceholderFactory(source=version.content)
        target_placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()

        plugin = add_plugin(
            source_placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"
        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_move_plugin_uri(plugin)
            data = {
                "plugin_id": plugin.pk,
                "placeholder_id": target_placeholder.pk,
                "target_language": version.content.language,
                "move_a_copy": "true",
                "target_position": 1,
            }

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_cut_plugin(self):
        version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()
        user_settings = UserSettings.objects.create(
            language=version.content.language,
            user=self.get_superuser(),
            clipboard=Placeholder.objects.create(slot="clipboard"),
        )

        plugin = add_plugin(
            placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_move_plugin_uri(plugin)
            data = {
                "plugin_id": plugin.pk,
                "target_language": version.content.language,
                "placeholder_id": user_settings.clipboard_id,
            }

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)

    def test_move_plugin(self):
        version = factories.PageVersionFactory()
        source_placeholder = factories.PlaceholderFactory(source=version.content)
        target_placeholder = factories.PlaceholderFactory(source=version.content)
        poll = factories.PollFactory()

        plugin = add_plugin(
            source_placeholder, "PollPlugin", version.content.language, poll=poll
        )
        plugin.page.get_absolute_url = lambda *args, **kwargs: "/test_page/"  # Fake URL needed for URI

        dt = datetime(2016, 6, 6)
        with freeze_time(dt):
            endpoint = self.get_move_plugin_uri(plugin)
            data = {
                "plugin_id": plugin.pk,
                "target_language": version.content.language,
                "placeholder_id": target_placeholder.pk,
                "target_position": 1,
            }

            with self.login_user_context(self.get_superuser()):
                response = self.client.post(endpoint, data)
                self.assertEqual(response.status_code, 200)

        version = Version.objects.get(pk=version.pk)
        self.assertEqual(version.modified, dt)
