from cms.models import fields

from djangocms_versioning.helpers import is_content_editable


fields.PlaceholderRelationField.default_checks += [is_content_editable]
