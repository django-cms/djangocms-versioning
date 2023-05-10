from django import template

register = template.Library()


@register.inclusion_tag("polls/poll_tag.html", takes_context=True)
def render_poll(context, instance):
    pollcontent = instance.pollcontent_set.first()
    return {"content": pollcontent}
