from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import Text


@plugin_pool.register_plugin
class TextPlugin(CMSPluginBase):
    model = Text
    name = 'Text'
    allow_children = True
    render_template = 'text/text.html'
