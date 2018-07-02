from django.contrib import admin


class VersioningAdminMixin:
    pass


def versioning_admin_factory(admin_class):
    """A class factory returning admin class with overriden
    versioning functionality.

    :param admin_class: Existing admin class
    :return: A subclass of `VersioningAdminMixin` and `admin_class`
    """
    return type(admin_class.__name__, (VersioningAdminMixin, admin_class), {})


def replace_admin_for_model(model, admin_site=admin.site):
    """Checks if there's an existing admin class registered for `model`,
    and replaces it with a subclass that includes
    versioning functionality.

    :param model: Model class
    :param admin_site: AdminSite instance
    """
    try:
        admin_class = admin_site._registry[model].__class__
    except KeyError:
        # No admin class registered for given model. Skip.
        return
    else:
        new_admin_class = versioning_admin_factory(admin_class)
        admin_site.unregister(model)
        admin_site.register(model, new_admin_class)


def replace_admin_for_models(models):
    for model in models:
        replace_admin_for_model(model)
