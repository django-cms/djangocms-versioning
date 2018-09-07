from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.functional import cached_property

from cms import constants as cms_constants
from cms.apphook_pool import apphook_pool
from cms.cms_menus import CMSMenu, get_visible_nodes
from cms.models import PageContent
from cms.toolbar.utils import get_object_preview_url, get_toolbar_from_request
from cms.utils.page import get_page_queryset

from menus.base import Menu, Modifier, NavigationNode
from menus.menu_pool import menu_pool

from . import constants
from .models import Version


class CMSVersionedNavigationNode(NavigationNode):

    def __init__(self, *args, **kwargs):
        self.page_content_id = kwargs.pop('page_content_id')
        self.state = kwargs.pop('state')
        super().__init__(*args, **kwargs)

    def is_selected(self, request):
        try:
            page_id = request.current_page.pk
        except AttributeError:
            return False
        return page_id == self.id

    @cached_property
    def page_content(self):
        ct = ContentType.objects.get_for_model(PageContent)
        return ct.get_object_for_this_type(pk=self.page_content_id)


def _get_menu_node_for_page_content_version(renderer, version):
    page_content = version.content
    page = page_content.page
    language = renderer.request_language

    """ START Logic from cms.cms_menus.get_menu_node_for_page """
    attr = {
        'is_page': True,
        'soft_root': page.get_soft_root(language),
        'auth_required': page.login_required,
        'reverse_id': page.reverse_id,
    }

    limit_visibility_in_menu = page.get_limit_visibility_in_menu(language)

    if limit_visibility_in_menu is cms_constants.VISIBILITY_ALL:
        attr['visible_for_authenticated'] = True
        attr['visible_for_anonymous'] = True
    else:
        attr['visible_for_authenticated'] = limit_visibility_in_menu == cms_constants.VISIBILITY_USERS
        attr['visible_for_anonymous'] = limit_visibility_in_menu == cms_constants.VISIBILITY_ANONYMOUS

    attr['is_home'] = page.is_home
    extenders = []

    if page.navigation_extenders:
        if page.navigation_extenders in renderer.menus:
            extenders.append(page.navigation_extenders)
        elif '{0}:{1}'.format(page.navigation_extenders, page.pk) in renderer.menus:
            extenders.append('{0}:{1}'.format(page.navigation_extenders, page.pk))

    if page.title_cache.get(language) and page.application_urls:
        app = apphook_pool.get_apphook(page.application_urls)

        if app:
            extenders += app.get_menus(page, language)

    exts = []

    for ext in extenders:
        if hasattr(ext, 'get_instances'):
            exts.append('{0}:{1}'.format(ext.__name__, page.pk))
        elif hasattr(ext, '__name__'):
            exts.append(ext.__name__)
        else:
            exts.append(ext)

    if exts:
        attr['navigation_extenders'] = exts

    attr['redirect_url'] = page_content.redirect
    """ END Logic from cms.cms_menus.get_menu_node_for_page """

    if version.state == constants.PUBLISHED:
        url = page_content.get_absolute_url()
    else:
        url = get_object_preview_url(page_content)

    return CMSVersionedNavigationNode(
        title=page_content.menu_title or page_content.title + '-' + version.state,
        url=url,
        id=page.pk,
        attr=attr,
        visible=True,  # By default we set to True, VisibleNodesModifier will modify the nodes.
        page_content_id=page_content.pk,
        state=version.state,
    )


def _generate_nodes(renderer, version_nodes, home_page=None):
    menu_nodes = []
    node_id_to_page = {}
    language = renderer.request_language

    for version in version_nodes:
        page_content = version.content
        page = page_content.page
        node = page.node
        parent_id = node_id_to_page.get(node.parent_id)

        if node.parent_id and not parent_id:
            continue

        menu_node = _get_menu_node_for_page_content_version(renderer, version)
        cut_homepage = home_page and not home_page.get_in_navigation(language)

        if cut_homepage and parent_id == home_page.pk:
            # When the homepage is hidden from navigation,
            # we need to cut all its direct children from it.
            menu_node.parent_id = None
        else:
            menu_node.parent_id = parent_id

        node_id_to_page[node.pk] = page.pk
        menu_nodes.append(menu_node)
    return menu_nodes


class CMSVersionedMenu(Menu):

    def get_nodes(self, request):
        site = self.renderer.site
        language = self.renderer.request_language
        pages = get_page_queryset(site)
        pages = get_visible_nodes(request, pages, site)

        if not pages:
            return []

        try:
            home_page = [page for page in pages if page.is_home][0]
        except IndexError:
            home_page = None

        cms_extension = apps.get_app_config('djangocms_versioning').cms_extension
        all_drafts = []
        all_published = []

        for page in pages:
            versionable_item = cms_extension.versionables_by_grouper[page.__class__]
            page_contents = (
                versionable_item
                .for_grouper(page)
                .filter(language=language)
                .values_list('pk', flat=True)
            )
            content_type = ContentType.objects.get_for_model(page_contents.model)
            draft_version = (
                Version
                .objects
                .filter(
                    state=constants.DRAFT,
                    content_type=content_type,
                    object_id__in=page_contents,
                )
                .first()
            )
            published_version = (
                Version
                .objects
                .filter(
                    state=constants.PUBLISHED,
                    content_type=content_type,
                    object_id__in=page_contents,
                )
                .first()
            )

            if draft_version:
                all_drafts.append(draft_version)
            if published_version:
                all_published.append(published_version)

        if not (all_drafts or all_published):
            return []

        menu_nodes = (
            _generate_nodes(self.renderer, all_drafts, home_page) +
            _generate_nodes(self.renderer, all_published, home_page)
        )
        return menu_nodes


# Remove the core djangoCMS CMSMenu and register the new CMSVersionedMenu.
menu_pool.menus.pop(CMSMenu.__name__)
menu_pool.register_menu(CMSVersionedMenu)


class VisibleNodesModifier(Modifier):

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        # We need to do this before any post-cut of nodes.
        if not post_cut:
            toolbar = get_toolbar_from_request(request)
            edit_or_preview = toolbar.edit_mode_active or toolbar.preview_mode_active
            visible_nodes = []
            page_nodes = {}

            # First we aggregate draft/published nodes against page.
            for n in nodes:
                if n.id not in page_nodes:
                    page_nodes[n.id] = {n.state: n}
                else:
                    page_nodes[n.id].update({n.state: n})

            # Based on the toolbar mode we will cut the unnecessary nodes.
            for key, values in page_nodes.items():
                if edit_or_preview and constants.DRAFT in values:
                    new_node = values[constants.DRAFT]
                else:
                    try:
                        new_node = values[constants.PUBLISHED]
                    except KeyError:
                        # There is no published version for the page.
                        new_node = None

                # Last check to see whether page content is enabled in navigation.
                if new_node and new_node.page_content.in_navigation:
                    visible_nodes.append(new_node)
            return visible_nodes
        return nodes


menu_pool.register_modifier(VisibleNodesModifier)
