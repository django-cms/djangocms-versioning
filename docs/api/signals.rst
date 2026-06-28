Signals
=======

djangocms-versioning sends two signals around every version state change, so you can
hook in caching, search indexing, notifications, logging and similar side effects.

For worked examples, see :doc:`/howto/react_to_version_changes`.


Available Signals
-----------------

.. py:data:: pre_version_operation

    Sent **before** a version state change occurs.

    **Signal sender**: The content model class (e.g., ``PostContent``)


.. py:data:: post_version_operation

    Sent **after** a version state change has been completed successfully.

    **Signal sender**: The content model class (e.g., ``PostContent``)


Signal Parameters
-----------------

Both signals emit the following keyword arguments:

.. list-table:: Signal Parameters
   :widths: 20 60 20
   :header-rows: 1

   * - Parameter
     - Description
     - Type
   * - ``sender``
     - The content model class (e.g., PostContent, PageContent)
     - Model class
   * - ``obj``
     - The Version instance being operated on
     - Version
   * - ``operation``
     - The type of operation being performed
     - str (see Operations below)
   * - ``token``
     - A unique token to tie pre and post signals together
     - str (UUID)
   * - ``unpublished``
     - (For publish operations) List of versions that will be unpublished
     - list of Version objects
   * - ``to_be_published``
     - (For unpublish operations) List of versions that will be published as replacements
     - list of Version objects


Version Operations
------------------

The ``operation`` parameter can have one of these values (from ``djangocms_versioning.constants``):

.. list-table:: Version Operations
   :widths: 30 70
   :header-rows: 1

   * - Operation Constant
     - Description
   * - ``OPERATION_DRAFT``
     - A new draft version has been created (or version moved to draft state)
   * - ``OPERATION_PUBLISH``
     - A draft version has been published
   * - ``OPERATION_UNPUBLISH``
     - A published version has been unpublished
   * - ``OPERATION_ARCHIVE``
     - A draft version has been archived


Signal Token
------------

Each emission includes a unique ``token`` that ties the matching ``pre`` and ``post``
signals together. Use it to stash state in the ``pre`` handler and retrieve it in the
``post`` handler — for example to correlate the two halves of an operation in logs, to
time it, or to carry forward identifiers without holding a reference to the ``Version``:

.. code-block:: python

    signal_state = {}

    @receiver(pre_version_operation)
    def before_version_change(sender, obj, operation, token, **kwargs):
        signal_state[token] = {
            "start_time": timezone.now(),
            "operation": operation,
            "version_id": obj.pk,
        }

    @receiver(post_version_operation)
    def after_version_change(sender, obj, operation, token, **kwargs):
        state = signal_state.pop(token, {})
        duration = timezone.now() - state.get("start_time", timezone.now())
        print(f"Operation {operation} took {duration.total_seconds()}s")


.. _signal-execution-order:

Signal Execution Order
----------------------

A first-time publish (nothing to replace) emits just two signals —
``pre_version_operation`` then ``post_version_operation``, both with
``operation = OPERATION_PUBLISH``.

When the publish *replaces* an already-published version, that version is
unpublished as part of the same operation, so **four** signals fire. The new
version is published first; the old one is then unpublished; the ``post`` publish
signal comes last:

1. ``pre_version_operation`` — ``OPERATION_PUBLISH``, ``obj`` = the new version
2. The new version transitions ``draft`` → ``published``
3. ``pre_version_operation`` — ``OPERATION_UNPUBLISH``, ``obj`` = the old version, with ``to_be_published`` = the new version
4. The old version transitions ``published`` → ``unpublished``
5. ``post_version_operation`` — ``OPERATION_UNPUBLISH``, ``obj`` = the old version, with ``to_be_published`` = the new version
6. ``post_version_operation`` — ``OPERATION_PUBLISH``, ``obj`` = the new version, with ``unpublished`` = ``[old version]``

(The ``pre``/``post`` distinction in step labels is the ``signal``; steps 2 and 4
are state transitions that emit no signal of their own.)

.. note::

    This exact sequence is pinned by the test
    ``tests/test_signals.py::TestVersioningSignals.test_publish_signals_fired_with_to_be_published_and_unpublished``,
    so any change to the emission order will fail the test suite.
