================================
DjangoBatchDeleteMutation
================================

Will delete multiple instances of a model depending on supplied filters.
The returned arguments are:

-  ``deletionCount``: True if the instance was found and deleted.
-  ``deletedIds``: The ids of the deleted instances.
-  ``missedIds``: The ids of the missed instances.

Mutation input arguments:

+------------+-----------+
| Argument   | Type      |
+============+===========+
| ids        | [ID]!     |
+------------+-----------+

All meta arguments:

+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| Argument                 | type      | Default   | Description                                                                         |
+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| model                    | Model     | None      | The model. **Required**.                                                            |
+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| permissions              | Tuple     | None      | The permissions required to access the mutation                                     |
+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| login\_required          | Boolean   | None      | If true, the calling user has to be authenticated                                   |
+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+
| return\_field\_name      | String    | None      | The name of the return field within the mutation. The default is the camelCased name of the model                                                                                 |
+--------------------------+-----------+-----------+-------------------------------------------------------------------------------------+

.. code:: python

    class BatchDeleteUser(DjangoBatchDeleteMutation):
        class Meta:
            model = User

.. code::

    mutation {
        batchDeleteUser(ids: ["VXNlck5vZGU6MQ=="]){
            deletedIds
            missedIds
            deletionCount
        }
    }

