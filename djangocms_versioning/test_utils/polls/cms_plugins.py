from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import PollPlugin as Poll


@plugin_pool.register_plugin
class PollPlugin(CMSPluginBase):
    model = Poll
    name = "Poll"
    allow_children = True
    render_template = "polls/poll.html"
