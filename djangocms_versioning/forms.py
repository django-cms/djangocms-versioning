from functools import lru_cache

from django import forms
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from cms.forms.validators import validate_url_uniqueness

from . import versionables


class DuplicateForm(forms.Form):
    site = forms.ModelChoiceField(
        label=_("Site"),
        queryset=Site.objects.all(),
        help_text=_("Site in which the new page will be created"),
    )
    slug = forms.CharField(
        label=_("Slug"),
        max_length=255,
        widget=forms.TextInput(),
        help_text=_("The part of the title that is used in the URL"),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.page_content = kwargs.pop("page_content")
        super().__init__(*args, **kwargs)

    def clean_slug(self):
        slug = slugify(self.cleaned_data["slug"])
        if not slug:
            raise forms.ValidationError(_("Slug must not be empty."))
        return slug

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        language = self.page_content.language

        slug = cleaned_data["slug"]
        if self.page_content.page.node.parent:
            parent_path = self.page_content.page.node.parent.item.get_path(language)
            path = "%s/%s" % (parent_path, slug) if parent_path else slug
        else:
            path = cleaned_data["slug"]

        try:
            validate_url_uniqueness(
                cleaned_data["site"],
                path=path,
                language=language,
                user_language=language,
            )
        except forms.ValidationError as e:
            self.add_error("slug", e)
        else:
            cleaned_data["path"] = path

        return cleaned_data


class VersionContentChoiceField(forms.ModelChoiceField):
    """Form field used to display a list of grouper instances"""

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop("language")
        self.predefined_label_method = kwargs.pop("option_label_override")
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        """Overridden to allow customizing the labels of the groupers"""
        if self.predefined_label_method:
            return self.predefined_label_method(obj, self.language)
        else:
            return super().label_from_instance(obj)


class GrouperFormMixin:
    """Mixin used by grouper_form_factory to create the grouper select form class"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        versionable = versionables.for_content(self._content_model)
        queryset = versionable.grouper_choices_queryset()
        self.fields[versionable.grouper_field_name].queryset = queryset


@lru_cache()
def grouper_form_factory(content_model, language=None):
    """Returns a form class used for selecting a grouper to see versions of.
    Form has a single field - grouper - which is a model choice field
    with available grouper objects for specified content model.

    :param content_model: Content model class
    """
    versionable = versionables.for_content(content_model)
    return type(
        content_model.__name__ + "GrouperForm",
        (GrouperFormMixin, forms.Form),
        {
            "_content_model": content_model,
            versionable.grouper_field_name: VersionContentChoiceField(
                queryset=versionable.grouper_model.objects.all(),
                label=versionable.grouper_model._meta.verbose_name,
                option_label_override=versionable.grouper_selector_option_label,
                language=language,
            ),
        },
    )
