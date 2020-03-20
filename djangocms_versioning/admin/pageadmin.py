from django.conf.urls import url
from django.contrib.admin.utils import flatten_fieldsets, unquote
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from cms import api
from cms.extensions import extension_pool
from cms.models import PageContent

from djangocms_versioning import versionables
from djangocms_versioning.compat import DJANGO_GTE_21
from djangocms_versioning.forms import DuplicateForm
from djangocms_versioning.models import Version


class VersioningChangeListMixin:
    """Mixin used for ChangeList classes of content models."""

    def get_queryset(self, request):
        """Limit the content model queryset to latest versions only."""
        queryset = super().get_queryset(request)
        versionable = versionables.for_content(queryset.model)
        return queryset.filter(pk__in=versionable.distinct_groupers())


def versioning_change_list_factory(base_changelist_cls):
    """Generate a ChangeList class to use for the content model"""
    return type(
        "Versioned" + base_changelist_cls.__name__,
        (VersioningChangeListMixin, base_changelist_cls),
        {}
    )


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes of
    content models.
    """

    def save_model(self, request, obj, form, change):
        """
        Overrides the save method to create a version object
        when a content object is created
        """
        super().save_model(request, obj, form, change)
        if not change:
            if isinstance(obj, PageContent):
                # FIXME disabled version creation for `cms.PageContent`
                # here, as it's already done in `cms.api.create_title`
                return
            # create a new version object and save it
            Version.objects.create(content=obj, created_by=request.user)

    def get_queryset(self, request):
        """Override manager so records not in published state can be displayed"""
        from ..helpers import override_default_manager

        with override_default_manager(self.model, self.model._original_manager):
            queryset = super().get_queryset(request)
        return queryset

    def get_changelist(self, request, **kwargs):
        ChangeList = super().get_changelist(request, **kwargs)
        return versioning_change_list_factory(ChangeList)

    change_form_template = "djangocms_versioning/admin/mixin/change_form.html"

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """Add a link to the version table to the change form view"""
        if "versioning_fallback_change_form_template" not in context:
            context[
                "versioning_fallback_change_form_template"
            ] = super().change_form_template

        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_readonly_fields(self, request, obj=None):
        """Port permission code from django >= 2.1.

        In later versions of django if a user has view perms but no
        change perms, fields are set as read-only. This is not the case
        in django < 2.1.
        """
        if obj and not DJANGO_GTE_21:
            version = Version.objects.get_for_content(obj)
            if not version.check_modify.as_bool(request.user):
                if self.fields:
                    return self.fields
                if self.fieldsets:
                    return flatten_fieldsets(self.fieldsets)
                if self.form.declared_fields:
                    return self.form.declared_fields
                return list(
                    set(
                        [field.name for field in self.opts.local_fields]
                        + [field.name for field in self.opts.local_many_to_many]
                    )
                )
        return super().get_readonly_fields(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and DJANGO_GTE_21:
            version = Version.objects.get_for_content(obj)
            return version.check_modify.as_bool(request.user)
        return super().has_change_permission(request, obj)


class VersioningPageContentAdminMixin(VersioningAdminMixin):

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj:
            version = Version.objects.get_for_content(obj)
            if not version.check_modify.as_bool(request.user):
                form = self.get_form_class(request)
                if getattr(form, "fieldsets"):
                    fields = flatten_fieldsets(form.fieldsets)
                fields = list(fields)
                for f_name in ["slug", "overwrite_url"]:
                    fields.remove(f_name)
        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            version = Version.objects.get_for_content(obj)
            if not version.check_modify.as_bool(request.user):
                for f_name in ["slug", "overwrite_url"]:
                    form.declared_fields[f_name].widget.attrs["readonly"] = True
        return form

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        # we replace the duplicate with our function.
        old_urls = [v for v in super().get_urls() if 'duplicate' not in str(v.name)]
        new_urls = [
            url(
                r"^(.+)/duplicate-content/$",
                self.admin_site.admin_view(self.duplicate_view),
                name="{}_{}_duplicate".format(*info),
            ),
        ]
        return new_urls + old_urls

    @transaction.atomic
    def duplicate_view(self, request, object_id):
        """Duplicate a specified PageContent.

        Create a new page with content copied from provided PageContent.

        :param request: Http request
        :param object_id: PageContent ID (as a string)
        """
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )

        form = DuplicateForm(
            user=request.user,
            page_content=obj,
            initial={
                "site": obj.page.node.site,
                "slug": obj.page.get_slug(obj.language),
            },
        )
        info = (self.model._meta.app_label, self.model._meta.model_name)
        if request.method == "POST":
            form = DuplicateForm(request.POST, user=request.user, page_content=obj)
            if form.is_valid():
                new_page = obj.page.copy(
                    site=form.cleaned_data["site"],
                    parent_node=obj.page.node.parent,
                    translations=False,
                    permissions=False,
                    extensions=False,
                )

                new_page_content = api.create_title(
                    page=new_page,
                    language=obj.language,
                    slug=form.cleaned_data["slug"],
                    path=form.cleaned_data["path"],
                    title=obj.title,
                    template=obj.template,
                    created_by=request.user,
                )
                new_page.title_cache[obj.language] = new_page_content

                extension_pool.copy_extensions(
                    source_page=obj.page, target_page=new_page, languages=[obj.language]
                )

                placeholders = obj.get_placeholders()
                for source_placeholder in placeholders:
                    target_placeholder, created = new_page_content.placeholders.get_or_create(
                        slot=source_placeholder.slot
                    )
                    source_placeholder.copy_plugins(
                        target_placeholder, language=obj.language
                    )

                self.message_user(request, _("Page has been duplicated"))
                return redirect(reverse("admin:{}_{}_changelist".format(*info)))

        context = dict(
            obj=obj,
            form=form,
            object_id=object_id,
            duplicate_url=reverse(
                "admin:{}_{}_duplicate".format(*info), args=(obj.pk,)
            ),
            back_url=reverse("admin:{}_{}_changelist".format(*info)),
        )
        return render(
            request, "djangocms_versioning/admin/duplicate_page_confirmation.html", context
        )
