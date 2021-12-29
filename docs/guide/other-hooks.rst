====================
Other hooks
====================

These hooks are class methods of a mutation, which can be overridden with custom behavior.

``before_mutate``
-------------------

.. list-table::
  :widths: 25 75 10
  :header-rows: 1

  * - Mutation
    - Arguments
    - Note
  * - create
    - cls, root, info, input
    - 1
  * - patch/update
    - cls, root, info, input, id
    - 1
  * - delete
    - cls, root, info, id
    -
  * - batch_create
    - cls, root, info, input
    - 1
  * - batch_patch/batch_update
    - cls, root, info, input
    - 1
  * - batch_delete/filter_delete
    - cls, root, info, input
    - 1

| **1:** The hook can modify and return the ``input`` object. Returning ``None`` will cause the mutation to use the original ``input``.

``before_save``
-------------------

.. list-table::
  :widths: 25 75 10
  :header-rows: 1

  * - Mutation
    - Arguments
    - Note
  * - create
    - cls, root, info, input, obj
    - 1
  * - patch/update
    - cls, root, info, input, id, obj
    - 1
  * - delete
    - cls, root, info, id, obj
    - 1
  * - batch_create
    - cls, root, info, input, created_objects
    - 2
  * - batch_patch/batch_update
    - cls, root, info, input, updated_objects
    - 2
  * - batch_delete
    - cls, root, info, ids, qs_to_delete
    - 3
  * - filter_delete
    - cls, root, info, filter_qs
    - 3

| **1:** You can optionally modify and return the ORM object ``obj``.
| **2:** You can optionally modify and return the ORM objects in ``created_objects`` or ``updated_objects``.
| **3:** You can optionally modify and return the querysets.

``after_mutate``
-------------------

.. list-table::
  :widths: 25 75 10
  :header-rows: 1

  * - Mutation
    - Arguments
    - Note
  * - create
    - cls, root, info, input, obj, return_data
    - 1
  * - patch/update
    - cls, root, info, id, input, obj, return_data
    - 1
  * - delete
    - cls, root, info, deleted_id, found
    -
  * - batch_create
    - cls, root, info, input, created_objs, return_data
    - 1
  * - batch_patch/batch_update
    - cls, root, info, input, updated_objs, return_data
    - 1
  * - batch_delete/filter_delete
    - cls, root, info, input, deletion_count, ids
    -

| **1:** You can modify and return the ``return_data`` argument.
