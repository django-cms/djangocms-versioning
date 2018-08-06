from django.contrib.contenttypes.fields import GenericForeignKey

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
    rel = models.ManyToManyfield(ManyToManyF)


### Many-to-Many Backwards Relationship ###
class GrouperManytoManyB(models.Model):
    pass


class ContentManytoManyB(models.Model):
    grouper = models.ForeignKey(GrouperManytoManyB)


### One-to-Many Generic Forwards Relationship ###
class GrouperGenericF(models.Model):
    pass


class GenericF(models.Model):
    pass


class ContentGenericF(models.Model):
    grouper = models.ForeignKey(GrouperGenericF)
    rel = GenericForeignKey(GenericF)


### One-to-Many Generic Backwards Relationship ###
class GrouperGenericB(models.Model):
    pass


class ContentGenericB(models.Model):
    grouper = models.ForeignKey(GrouperGenericB)


class GenericB(models.Model):
    rel = GenericForeignKey(ContentGenericB)


### A longer chain of relationships ###
class GrouperMultipleRelationships(models.Model):
    pass


class MultipleRelationshipsC(models.Model):
    pass


class MultipleRelationshipsB(models.Model):
    rel = models.ForeignKey(MultipleRelationshipsC)


class MultipleRelationshipsA(models.Model):
    rel = models.ForeignKey(MultipleRelationshipsB)


class ContentMultipleRelationships(models.Model):
    grouper = models.ForeignKey(Grouper1toManyF)
    rel = models.ForeignKey(MultipleRelationshipsA)
