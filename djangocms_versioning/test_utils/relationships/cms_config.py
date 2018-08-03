from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem


class RelationshipsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = []
