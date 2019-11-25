================================
DjangoBatchDeleteMutation
================================

Will delete multiple instances of a model depending on supplied filters.
The returned arguments are:

-  ``deletionCount``: True if the instance was found and deleted.
-  ``deletedIds``: The ids of the deleted instances.

Mutation input arguments:

+------------+-----------+
| Argument   | Type      |
+============+===========+
| input      | Object!   |
+------------+-----------+

All meta arguments:

+-------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| Argument          | type      | Default   | Description                                                                         |
+===================+===========+===========+=====================================================================================+
| model             | Model     | None      | The model. **Required**.                                                            |
+-------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| filter\_fields    | Tuple     | ()        | A number of filter fields which allow us to restrict the instances to be deleted.   |
+-------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| permissions       | Tuple     | None      | The permissions required to access the mutation                                     |
+-------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| login\_required   | Boolean   | None      | If true, the calling user has to be authenticated                                   |
+-------------------+-----------+-----------+-------------------------------------------------------------------------------------+

If there are multiple filters, these will be combined with
**and**-clauses. For or-clauses, use multiple mutation calls.

.. code:: python

    class BatchDeleteUser(DjangoBatchDeleteMutation):
        class Meta:
            model = User
            filter_fields = ('name', 'house__address',)

.. code:: graphql

    mutation {
        batchDeleteUser(input: {name: 'John'}){
            deletedIds
            deletionCount
        }
    }

