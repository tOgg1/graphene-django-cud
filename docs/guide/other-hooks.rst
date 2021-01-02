====================
Other hooks
====================

These hooks are class methods of a mutation, which can be overriden with custom behavior.


``before_mutate``
-------------------

The first hook that fires during the mutation process.

For create, batch-create, batch-delete and filter-delete mutations, the hook is:

``before_mutate(cls, root, info, input)``

For update/delete mutations, the hook is

``before_mutate(cls, root, info, input, id)``

In both cases, the hook can modify and return the ``input`` object. Returning ``None``
will cause the mutation to use the original ``input``.

``before_save``
-------------------

For create/update/delete mutations, the hook is:

``before_save(cls, root, info, input, obj)``

And can optionally modify and return the ORM object ``obj``.

For batch-create mutations, the hook is:

``before_save(cls, root, info, created_objects)``

For batch-delete and filter-delete, the hook is:

``before_save(cls, root, info, qs_to_delete)``

and 

``before_save(cls, root, info, filter_qs)``

And can optionally modify and return the queryset.

``after_mutate``
-------------------

For create/update, the hook is:

``after_mutate(cls, root, info, obj, return_data)``

and for batch-create:

``after_mutate(cls, root, info, created_objs, return_data)``

Both allow you to modify and return the ``return_data`` argument.

For delete, the hook is:

``after_mutate(cls, root, info, deleted_id, found)``

For batch-delete and filter-delete, the hook is:

``after_mutate(cls, root, info, deletion_count, deleted_ids)``