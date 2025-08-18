from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning.plugin_rendering import VersionContentRenderer
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    PlaceholderFactory,
    PollVersionFactory,
)


class MonkeypatchTestCase(CMSTestCase):
    def test_prefetch_versioned_m2m_objects(self):
        '''
        test model with manytomany field to grouper model
        '''
        request = self.get_request('/')
        toolbar = CMSToolbar(request)
        toolbar.edit_mode_active = True
        request.toolbar = toolbar
        context = {"request": request}
        contentRenderer = VersionContentRenderer(request)

        version = PageVersionFactory()
        placeholder = PlaceholderFactory(source=version.content)
        poll_version = PollVersionFactory(content__language='en')
        poll = poll_version.content.poll

        plugin = add_plugin(
            placeholder, "PollManyPlugin", version.content.language
        )

        plugin.polls.add(poll)
        plugin._prefetched_objects_cache = {}

        with self.assertNumQueries(1):
            contentRenderer.render_plugin(plugin, context)
            for i in range(1000):
                self.assertEqual(1, len(plugin.polls.all()))

        with self.assertNumQueries(0):
            self.assertEqual(1, len(plugin.polls.all()))

        self.assertIsNotNone(plugin._prefetched_objects_cache)
        self.assertIsNotNone(plugin._prefetched_objects_cache['polls'])
        self.assertEqual(len(plugin._prefetched_objects_cache['polls']), 1)

    def test_prefetch_versioned_m2o_objects(self):
        '''
        #test model with one foreign key to grouper model
        '''
        request = self.get_request('/')
        toolbar = CMSToolbar(request)
        toolbar.edit_mode_active = True
        request.toolbar = toolbar
        context = {"request": request}
        contentRenderer = VersionContentRenderer(request)

        version = PageVersionFactory()
        placeholder = PlaceholderFactory(source=version.content)
        poll_version = PollVersionFactory(content__language='en')
        poll = poll_version.content.poll

        plugin = add_plugin(
            placeholder, "PollPlugin", version.content.language, poll=poll
        )

        contentRenderer.render_plugin(plugin, context)
        self.assertIsNotNone(plugin.poll._prefetched_objects_cache)