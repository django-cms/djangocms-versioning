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
