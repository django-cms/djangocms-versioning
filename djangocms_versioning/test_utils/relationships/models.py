from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from django.db import models


### One-to-One Forwards Relationship ###
class Grouper1to1F(models.Model):
    pass


class OneToOneF(models.Model):
    pass


class Content1to1F(models.Model):
    grouper = models.ForeignKey(Grouper1to1F)
    rel = models.OneToOneField(OneToOneF)


### One-to-One Backwards Relationship ###
class Grouper1to1B(models.Model):
    pass


class Content1to1B(models.Model):
    grouper = models.ForeignKey(Grouper1to1B)


class OneToOneB(models.Model):
    rel = models.OneToOneField(Content1to1B)


### One-to-Many Forwards Relationship ###
class Grouper1toManyF(models.Model):
    pass


class OneToManyF(models.Model):
    pass


class Content1toManyF(models.Model):
    grouper = models.ForeignKey(Grouper1toManyF)
    rel = models.ForeignKey(OneToManyF)


### One-to-Many Backwards Relationship ###
class Grouper1toManyB(models.Model):
    pass


class Content1toManyB(models.Model):
    grouper = models.ForeignKey(Grouper1toManyB)


class OneToManyB(models.Model):
    rel = models.ForeignKey(Content1toManyB)


### Many-to-Many Forwards Relationship ###
class GrouperManytoManyF(models.Model):
    pass


class ManyToManyF(models.Model):
    pass


class ContentManytoManyF(models.Model):
    grouper = models.ForeignKey(GrouperManytoManyF)
    rel = models.ManyToManyField(ManyToManyF)


### Many-to-Many Backwards Relationship ###
class GrouperManytoManyB(models.Model):
    pass


class ContentManytoManyB(models.Model):
    grouper = models.ForeignKey(GrouperManytoManyB)


class ManyToManyB(models.Model):
    rel = models.ManyToManyField(ContentManytoManyB)


### Generic FK Relationship ###
class GrouperGeneric(models.Model):
    pass


class ContentGeneric(models.Model):
    grouper = models.ForeignKey(GrouperGeneric)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )
    object_id = models.PositiveIntegerField()
    rel = GenericForeignKey('content_type', 'object_id')