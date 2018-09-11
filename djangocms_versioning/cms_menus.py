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
        self.draft_id = kwargs.pop('draft_id')
        self.published_id = kwargs.pop('published_id')
        super().__init__(*args, **kwargs)

    def is_selected(self, request):
        try:
            page_id = request.current_page.pk
        except AttributeError:
            return False
        return page_id == self.id

    @cached_property
    def draft_page_content(self):
        if self.draft_id:
            ct = ContentType.objects.get_for_model(PageContent)
            return ct.get_object_for_this_type(pk=self.draft_id)
        return None

    @cached_property
    def published_page_content(self):
        if self.published_id:
            ct = ContentType.objects.get_for_model(PageContent)
            return ct.get_object_for_this_type(pk=self.published_id)
        return None


def _get_attrs_for_page_node(renderer, page):
    language = renderer.request_language
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
    return attr


def _create_node_for_page_content_version(renderer, version):
    page = version['page']

    draft_content_id = (
        version[constants.DRAFT].content.pk
        if version[constants.DRAFT] else None
    )
    published_content_id = (
        version[constants.PUBLISHED].content.pk
        if version[constants.PUBLISHED] else None
    )

    return CMSVersionedNavigationNode(
        id=page.pk,
        attr=_get_attrs_for_page_node(renderer, page),
        title='',
        url='',
        draft_id=draft_content_id,
        published_id=published_content_id,
    )


def _generate_ancestor_hierarchy(page_nodes):
    menu_nodes = []
    node_id_to_page = {}

    for page_node in page_nodes.copy():
        node = page_node['node']
        page = page_node['page']
        page_tree_node = page.node
        parent_id = node_id_to_page.get(page_tree_node.parent_id)

        if page_tree_node.parent_id and not parent_id:
            # If the parent page is not available (unpublished, etc..),
            # we skip adding the menu node.
            continue

        node.parent_id = parent_id
        node_id_to_page[page_tree_node.pk] = page.pk
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
        page_content_versions = []

        # Get the latest draft and published version for each visible page.
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

            version = None

            if draft_version or published_version:
                version = {
                    'page': page,
                    constants.DRAFT: draft_version,
                    constants.PUBLISHED: published_version,
                }
            if version:
                page_content_versions.append(version)

        if not page_content_versions:
            return []

        # Create the menu nodes for the page content versions.
        menu_nodes = []

        for version in page_content_versions:
            n = _create_node_for_page_content_version(self.renderer, version)
            menu_nodes.append({'page': version['page'], 'node': n})

        # Set the parent_id for each node in order to generate
        # the menu hierarchy and return the nodes.
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
            menu_nodes = []
            home_page_content = None

            for node in page_nodes.copy():
                # Always try to get the draft version if in edit/preview mode.
                # Fallback to published if no draft is found.
                # If NOT in edit/preview mode, always get published version.
                if edit_or_preview and node.draft_page_content:
                    state = constants.DRAFT
                    page_content = node.draft_page_content
                else:
                    state = constants.PUBLISHED
                    page_content = node.published_page_content

                if not page_content:
                    # This will be the case where request is public and the
                    # current node only has a draft version.
                    continue

                if not page_content.in_navigation:
                    # User has selected not show in navigation.
                    # Check whether current node is home page. This will be used to
                    # cut the direct children of the home page.
                    if page_content.page.is_home:
                        home_page_content = page_content
                    continue

                # Set title and url.
                node.title = page_content.menu_title or page_content.title

                if state == constants.DRAFT:
                    node.url = get_object_preview_url(page_content)
                else:
                    node.url = page_content.get_absolute_url()

                # Set redirect_url attr.
                node.attr['redirect_url'] = page_content.redirect

                # Next we need to remove the draft children
                # for the node when on public mode.
                if not edit_or_preview:
                    for child in node.children.copy():
                        if not child.published_page_content:
                            node.children.remove(child)

                # When the homepage is hidden from navigation,
                # we need to cut all its direct children from it.
                if home_page_content and home_page_content.page.pk == node.parent_id:
                    node.parent_id = None

                # All good.
                menu_nodes.append(node)
            return menu_nodes
        return nodes


menu_pool.register_modifier(VisibleNodesModifier)
