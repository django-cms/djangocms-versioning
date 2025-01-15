from __future__ import annotations

from functools import lru_cache

from django import forms
from django.contrib.admin.widgets import AutocompleteSelect

from . import versionables


class VersionAutocompleteSelect(AutocompleteSelect):
    def optgroups(self, name: str, value: str, attr: dict | None = None):
        default = (None, [], 0)
        default[1].append(self.create_option(name, "", "", False, 0))
        return [default]


class VersionContentChoiceField(forms.ModelChoiceField):
    """Form field used to display a list of grouper instances"""

    def __init__(self, *args, model=None, admin_site=None, **kwargs):
        self.language = kwargs.pop("language")
        self.predefined_label_method = kwargs.pop("option_label_override")
        if getattr(admin_site._registry.get(model), "search_fields", []):
            # If the model is registered in the admin, use the autocomplete widget
            kwargs.setdefault("widget", VersionAutocompleteSelect(
                model._meta.get_field(versionables.for_content(model).grouper_field_name),
                admin_site=admin_site,
            ))
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        """Overridden to allow customizing the labels of the groupers"""
        if self.predefined_label_method:
            return self.predefined_label_method(obj, self.language)
        else:
            return super().label_from_instance(obj)


@lru_cache
def grouper_form_factory(content_model, language=None, admin_site=None):
    """Returns a form class used for selecting a grouper to see versions of.
    Form has a single field - grouper - which is a model choice field
    with available grouper objects for specified content model.

    :param content_model: Content model class
    :param language: Language
    """
    if admin_site is None:
        from django.contrib.admin import site
        admin_site = site

    versionable = versionables.for_content(content_model)
    return type(
        content_model.__name__ + "GrouperForm",
        (forms.Form,),
        {
            "_content_model": content_model,
            versionable.grouper_field_name: VersionContentChoiceField(
                label=versionable.grouper_model._meta.verbose_name.capitalize(),
                queryset=versionable.grouper_model.objects.all(),
                option_label_override=versionable.grouper_selector_option_label,
                admin_site=admin_site,
                model=content_model,
                language=language,
            ),
        },
    )
