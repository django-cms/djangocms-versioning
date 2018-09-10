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
        title=page_content.menu_title or page_content.title,
        url=url,
        id=page.pk,
        attr=attr,
        visible=True,  # By default we set to True, VisibleNodesModifier will modify the nodes.
        page_content_id=page_content.pk,
        state=version.state,
    )


def _generate_ancestor_hierarchy(page_nodes):
    menu_nodes = []
    node_id_to_page = {}

    try:
        home_page_content = [
            n.page_content for n in page_nodes
            if n.page_content.page.is_home
        ][0]
    except IndexError:
        home_page_content = None

    for node in page_nodes.copy():
        page_content = node.page_content
        page = page_content.page
        page_node = page.node
        parent_id = node_id_to_page.get(page_node.parent_id)

        if page_node.parent_id and not parent_id:
            # If the parent page is not available (unpublished, etc..),
            # we skip adding the menu node.
            continue

        cut_homepage = home_page_content and not home_page_content.in_navigation

        if cut_homepage and parent_id == home_page_content.page.pk:
            # When the homepage is hidden from navigation,
            # we need to cut all its direct children from it.
            node.parent_id = None
        else:
            node.parent_id = parent_id

        node_id_to_page[page_node.pk] = page.pk
        menu_nodes.append(node)
    return menu_nodes


class CMSVersionedMenu(Menu):

    def get_nodes(self, request):
        site = self.renderer.site
        language = self.renderer.request_language
        pages = get_page_queryset(site)
        pages = get_visible_nodes(request, pages, site)

        if not pages:
            return []

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

        # Create the menu nodes for draft and published versions.
        menu_nodes = []

        for version in all_drafts + all_published:
            menu_nodes.append(_get_menu_node_for_page_content_version(self.renderer, version))

        # We now set the parent_id for each visible node to
        # generate the menu hierarchy.
        return _generate_ancestor_hierarchy(menu_nodes)


# Remove the core djangoCMS CMSMenu and register the new CMSVersionedMenu.
menu_pool.menus.pop(CMSMenu.__name__)
menu_pool.register_menu(CMSVersionedMenu)


class VisibleNodesModifier(Modifier):

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        # We need to do this before any post-cut of nodes.
        if not post_cut:
            toolbar = get_toolbar_from_request(request)
            edit_or_preview = toolbar.edit_mode_active or toolbar.preview_mode_active
            page_nodes = [n for n in nodes if n.attr['is_page']]
            visible_nodes = []
            page_aggr_nodes = {}

            # First we aggregate draft/published nodes against page.
            for n in page_nodes:
                if n.id not in page_aggr_nodes:
                    page_aggr_nodes[n.id] = {n.state: n}
                else:
                    page_aggr_nodes[n.id].update({n.state: n})

            # Based on the toolbar mode we will cut the unnecessary nodes.
            for key, values in page_aggr_nodes.items():
                # Always return DRAFT when in edit or preview mode if exists.
                if edit_or_preview and constants.DRAFT in values:
                    new_node = values[constants.DRAFT]
                    draft_children = [n.id for n in new_node.children]

                    # Check if current draft node has published node children.
                    try:
                        published_version_children = values[constants.PUBLISHED].children
                    except KeyError:
                        published_version_children = []

                    # Merge publish version children to draft node children.
                    for n in published_version_children:
                        if n.id not in draft_children:
                            new_node.children.append(n)

                    new_node.children = sorted(new_node.children, key=lambda n: n.id)
                else:
                    # Fallback to PUBLISHED.
                    try:
                        new_node = values[constants.PUBLISHED]
                    except KeyError:
                        # There is no published version for the page.
                        new_node = None

                # Last check to see whether page content is enabled in navigation.
                if new_node and new_node.page_content.in_navigation:
                    visible_nodes.append(new_node)
            return sorted(visible_nodes, key=lambda n: n.id)
        return nodes


menu_pool.register_modifier(VisibleNodesModifier)
