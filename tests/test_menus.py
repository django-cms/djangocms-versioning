from cms import constants as cms_constants
from cms.cms_menus import CMSMenu as OriginalCMSMenu
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar
from cms.toolbar.utils import get_object_preview_url
from django.contrib.auth.models import AnonymousUser
from django.template import Context, Template
from django.test import RequestFactory
from django.test.utils import override_settings
from menus.menu_pool import menu_pool

from djangocms_versioning.cms_menus import CMSMenu
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    UserFactory,
)


class CMSVersionedMenuTestCase(CMSTestCase):
    def setUp(self):
        super().setUp()
        from djangocms_versioning.test_utils.factories import TreeNode

        def get_page(title, path, parent=None):
            return {
                "content__title": title,
                "content__menu_title": "",
                "content__in_navigation":  True,
                "content__limit_visibility_in_menu":  None,
                "content__language": "en",
                "content__page__node__path" if TreeNode else "content__page__path": path,
                "content__page__node__parent" if TreeNode else "content__page__parent": parent,
            }
        self._page_1 = PageVersionFactory(**get_page("page_content_1", "0001"))
        self._page_2 = PageVersionFactory(**get_page("page_content_2", "0002"))
        self._page_2_1 = PageVersionFactory(**get_page(
            "page_content_2_1",
            "00020001",
            self._page_2.content.page.node if TreeNode else self._page_2.content.page,
        ))
        self._page_2_2 = PageVersionFactory(**get_page(
            "page_content_2_2",
            "00020002",
            self._page_2.content.page.node if TreeNode else self._page_2.content.page,
        ))
        self._page_3 = PageVersionFactory(**get_page("page_content_3", "0003"))

    def _render_menu(self, user=None, **kwargs):
        request = RequestFactory().get("/")

        if not user:
            is_auth_user = kwargs.get("is_auth_user", True)
            user = self.get_superuser() if is_auth_user else AnonymousUser()

        request.user = user
        request.session = {}
        toolbar = CMSToolbar(request)

        if kwargs.get("edit_mode", False):
            toolbar.edit_mode_active = True
            toolbar.preview_mode_active = False
        elif kwargs.get("preview_mode", False):
            toolbar.edit_mode_active = False
            toolbar.preview_mode_active = True
        else:
            toolbar.edit_mode_active = False
            toolbar.preview_mode_active = False

        request.toolbar = toolbar
        context = {"request": request}
        template = Template("{% load menu_tags %}" "{% show_menu 0 100 100 100 %}")
        template.render(Context(context))
        return context

    def _assert_node(self, node, version, edit_or_preview=True):
        content = version.content
        self.assertEqual(node.title, content.title)

        if edit_or_preview:
            self.assertEqual(node.url, get_object_preview_url(content))
        else:
            self.assertEqual(node.url, content.get_absolute_url())

    def test_core_cms_menu_is_removed(self):
        menu_pool.discover_menus()
        registered_menus = menu_pool.get_registered_menus(for_rendering=True)
        self.assertNotIn(OriginalCMSMenu, registered_menus.values())
        self.assertIn(CMSMenu, registered_menus.values())

    def test_no_menu_if_no_published_pages_in_public_mode(self):
        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 0)

    def test_show_menu_with_draft_pages_in_edit_mode(self):
        context = self._render_menu(edit_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_2)
        children = nodes[1].children
        self.assertEqual(len(children), 2)
        self._assert_node(children[0], self._page_2_1)
        self._assert_node(children[1], self._page_2_2)
        self._assert_node(nodes[2], self._page_3)

    def test_show_menu_with_draft_pages_in_preview_mode(self):
        context = self._render_menu(edit_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_2)
        children = nodes[1].children
        self.assertEqual(len(children), 2)
        self._assert_node(children[0], self._page_2_1)
        self._assert_node(children[1], self._page_2_2)
        self._assert_node(nodes[2], self._page_3)

    def test_show_menu_with_published_nodes_only_in_public_mode(self):
        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)

        # Publish Page 1.
        self._page_1.publish(self.get_superuser())

        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_1, False)

    def test_not_show_published_child_node_if_parent_is_draft_in_public_mode(self):
        # Publish Page 1.
        self._page_1.publish(self.get_superuser())

        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_1, False)

        # Publish Page 2_1. This should not be rendered because
        # Page 2 is not published.
        self._page_2_1.publish(self.get_superuser())

        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_1, False)

    def test_show_child_node_if_parent_is_published_in_public_mode(self):
        # Publish Page 2 and Page 2_1.
        self._page_2.publish(self.get_superuser())
        self._page_2_1.publish(self.get_superuser())

        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_2, False)
        children = nodes[0].children
        self.assertEqual(len(children), 1)
        self._assert_node(children[0], self._page_2_1, False)

        # Publish Page 2_1.
        self._page_2_2.publish(self.get_superuser())

        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_2, False)
        children = nodes[0].children
        self.assertEqual(len(children), 2)
        self._assert_node(children[0], self._page_2_1, False)
        self._assert_node(children[1], self._page_2_2, False)

    def test_not_show_child_node_if_not_in_navigation(self):
        # Page 2_1 hidden in navigation.
        self._page_2_1.content.in_navigation = False
        self._page_2_1.content.save()

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_2)
        children = nodes[1].children
        self.assertEqual(len(children), 1)
        self._assert_node(children[0], self._page_2_2)
        self._assert_node(nodes[2], self._page_3)

    def test_not_show_nodes_if_hidden_in_navigation(self):
        # Hide Page 1 and Page 2_1 in navigation.
        self._page_1.content.in_navigation = False
        self._page_1.content.save()
        self._page_2_1.content.in_navigation = False
        self._page_2_1.content.save()

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 2)
        self._assert_node(nodes[0], self._page_2)
        children = nodes[0].children
        self.assertEqual(len(children), 1)
        self._assert_node(children[0], self._page_2_2)
        self._assert_node(nodes[1], self._page_3)

    def test_not_show_child_nodes_if_parent_not_in_navigation(self):
        # Page 2 hidden in navigation.
        self._page_2.content.in_navigation = False
        self._page_2.content.save()

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 2)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_3)

    def test_show_home_page_children_nodes_even_if_home_page_is_hidden_in_navigation(
        self
    ):
        # Make Page 2 home and hide in navigation.
        self._page_2.content.page.is_home = True
        self._page_2.content.page.save()
        self._page_2.content.in_navigation = False
        self._page_2.content.save()

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 4)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_2_1)
        self._assert_node(nodes[2], self._page_2_2)
        self._assert_node(nodes[3], self._page_3)

    def test_show_published_nodes_if_draft_not_exist_in_non_public_mode(self):
        # Publish Page 2 and Page 2_2.
        self._page_2.publish(self.get_superuser())
        self._page_2_2.publish(self.get_superuser())

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], self._page_2)
        children = nodes[1].children
        self.assertEqual(len(children), 2)
        self._assert_node(children[0], self._page_2_1)
        self._assert_node(children[1], self._page_2_2)
        self._assert_node(nodes[2], self._page_3)

    def test_show_draft_nodes_if_draft_exist_in_non_public_mode(self):
        # Publish Page 2 and Page 2_2.
        self._page_2.publish(self.get_superuser())
        self._page_2_2.publish(self.get_superuser())
        # Create new drafts for both Page 2 and Page 2_2.
        _page_2_new_draft = self._page_2.copy(self.get_superuser())
        _page_2_2_new_draft = self._page_2_2.copy(self.get_superuser())
        # Make some changes to the new drafts (Just to verify).
        _page_2_new_draft.content.title = "page_content_2_new_draft"
        _page_2_new_draft.content.save()
        _page_2_2_new_draft.content.title = "page_content_2_2_new_draft"
        _page_2_2_new_draft.content.save()

        context = self._render_menu(preview_mode=True)
        nodes = context["children"]
        self.assertEqual(len(nodes), 3)
        self._assert_node(nodes[0], self._page_1)
        self._assert_node(nodes[1], _page_2_new_draft)
        children = nodes[1].children
        self.assertEqual(len(children), 2)
        self._assert_node(children[0], self._page_2_1)
        self._assert_node(children[1], _page_2_2_new_draft)
        self._assert_node(nodes[2], self._page_3)

    def test_attr_set_properly_to_node(self):
        # To test the attr.limit_visibility_in_menu we will set
        # to cms_constants.VISIBILITY_USERS, so anonymous users
        # cannot see the menu node for Page 1.
        self._page_1.content.limit_visibility_in_menu = cms_constants.VISIBILITY_USERS
        self._page_1.content.save()
        self._page_1.publish(self.get_superuser())

        # Test for anonymous user.
        context = self._render_menu(is_auth_user=False)
        nodes = context["children"]
        self.assertEqual(len(nodes), 0)

        # Test for logged in user.
        context = self._render_menu()
        nodes = context["children"]
        self.assertEqual(len(nodes), 1)
        self._assert_node(nodes[0], self._page_1, False)

    @override_settings(CMS_PUBLIC_FOR="staff")
    def test_show_menu_only_visible_for_user(self):
        from cms.models import ACCESS_PAGE, PagePermission
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="test_group")
        user = UserFactory()
        user.groups.add(group)
        q_args = {"grant_on": ACCESS_PAGE, "group": group}
        # Restrict pages for the user so that we can test
        # whether the can_view=True only pages are visible in the menu.
        PagePermission.objects.create(
            can_view=False, page=self._page_1.content.page, **q_args
        )
        PagePermission.objects.create(
            can_view=True, page=self._page_2.content.page, **q_args
        )
        PagePermission.objects.create(
            can_view=False, page=self._page_2_1.content.page, **q_args
        )
        PagePermission.objects.create(
            can_view=True, page=self._page_2_2.content.page, **q_args
        )
        PagePermission.objects.create(
            can_view=True, page=self._page_3.content.page, **q_args
        )

        context = self._render_menu(user=user, preview_mode=True)
        nodes = context["children"]
        # At this point, only Page 2, Page 2_2 and Page 3 should
        # be rendered in the menu.
        self.assertEqual(len(nodes), 2)
        self._assert_node(nodes[0], self._page_2)
        children = nodes[0].children
        self.assertEqual(len(children), 1)
        self._assert_node(children[0], self._page_2_2)
        self._assert_node(nodes[1], self._page_3)
