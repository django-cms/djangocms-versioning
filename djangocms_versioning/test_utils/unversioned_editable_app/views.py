from cms.toolbar.utils import get_toolbar_from_request
from django.http import Http404
from django.shortcuts import render

from .models import FancyPoll


def detail(request, poll_id):
    try:
        poll = FancyPoll.objects.get(pk=poll_id)
    except FancyPoll.DoesNotExist as err:
        raise Http404("Fancy Poll doesn't exist") from err

    toolbar = get_toolbar_from_request(request)
    toolbar.set_object(poll)
    return render(request, poll.template, {"poll": poll})


def render_content(request, content):
    return detail(request, content.pk)
