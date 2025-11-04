from __future__ import annotations

from urllib.parse import urljoin

from cms.toolbar.utils import get_object_preview_url
from cms.utils import get_current_site
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _

from djangocms_versioning import models
from djangocms_versioning.helpers import send_email


def get_full_url(location: str, site: Site | None = None) -> str:
    if not site:
        site = Site.objects.get_current()

    if getattr(settings, "USE_HTTPS", False):
        scheme = "https"
    else:
        scheme = "http"
    domain = f"{scheme}://{site.domain}"
    return urljoin(domain, location)


def notify_version_author_version_unlocked(version: models.Version, unlocking_user: settings.AUTH_USER_MODEL) -> int:
    # If the unlocking user is the current author, don't send a notification email
    if version.created_by == unlocking_user:
        return 0

    # If the users name is available use it, otherwise use their username
    username = unlocking_user.get_full_name() or unlocking_user.username

    site = get_current_site()
    recipients = [version.created_by.email]
    subject = "[Django CMS] ({site_name}) {title} - {description}".format(
        site_name=site.name,
        title=version.content,
        description=_("Unlocked"),
    )
    version_url = get_full_url(
        get_object_preview_url(version.content)
    )

    # Prepare and send the email
    template_context = {
        "version_link": version_url,
        "by_user": username,
    }
    status = send_email(
        recipients=recipients,
        subject=subject,
        template="unlock-notification.txt",
        template_context=template_context,
    )
    return status
