****************
django CMS Versioning
****************

============
Installation
============

Requirements
============

django CMS URL Manager requires that you have a django CMS 3.6 (or higher) project already running and set up.


To install
==========

Run::

    pip install djangocms-versioning

Add ``djangocms_versioning`` to your project's ``INSTALLED_APPS``.

Run::

    python manage.py migrate djangocms_versioning

to perform the application's database migrations.


=====
Usage
=====

## System explanation
There are four key terms or classes you need to understand in order to implement Versioning. Note that these are described here by their function - or role - in the Versioning system: the actual names of the classes in implementation are up to you. (This will be demonstrated in the examples below).

**Grouper** - an object used to group all versions of an object together - mandatory. This will have a one-to-many relationship with *Content*.

**Version** - an object with a one-to-one relation to a single content record - mandatory. This tracks additional information about that version such as start and end dates, as well as foreign key to *Campaign*. You would create this model and it should inherit from *BaseVersion* model included in Versioning models.py

**Content** - a single versioned object, must have a FK to a *Grouper* object - mandatory. If you are implementing Versioning on an existing content model then this will be that model. All you need to add is the foreign key to your *Grouper* model.

**ContentExtension** - an object which tracks additional information / relationships associated with the content - optional. This can be any model associated with your *Content* model. It may be a 121 or 12M or M2M relationship. It's your responsibility to implement versioning for these extensions via the Version::copy_content method in your implementation of the *Version* class described above.

The key things needed in order to implement DjangoCMS Versioning are:

1. Create a *Grouper* model:
If you are implementing Versioning on a new content-type model, then it's suggested that you use the terms above. So for example if you're building the polls app then you would create Poll (as the *Grouper* model) and PollContent (as the *Content* model).
If you are implementing Versioning on an existing content-type model where you don't want to change the name of the *Content* model, then it is suggested that you add a *Grouper* model. So for example if you're implementing Versioning on an existing poll application where you've already defined Poll as your *Content* model and you have data in that model, then that existing model maps to our *Content* term. You would then add a new PollGrouper (or PollVersionGroup) model as the *Grouper*.
1. Link your *Grouper* to your *Content* model by assigning a value to `grouper_field` property of *Version*. This value can either be a reference to the *Grouper* class or just it's name. If you don't do this you'll get an error, which will remind you to do it.
1. Create the Version model:
Continuing the polls example above, you could add PollVersions inheriting from djangocms-versioning.models.BaseVersion. 
1. Implement your ContentExtension copying in the PollVersions copy_content method

An example implementation can be found here: 
https://github.com/divio/djangocms-versioning/blob/master/djangocms_versioning/test_utils/polls/models.py



