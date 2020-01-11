================================
DjangoDeleteMutation
================================

Will delete an existing instance of a model. The returned arguments are:

-  ``found``: True if the instance was found and deleted.
-  ``deletedId``: THe id of the deleted instance.

Mutation input arguments:

+------------+--------+
| Argument   | Type   |
+============+========+
| id         | ID!    |
+------------+--------+

All meta arguments:

+-------------------+-----------+-----------+-----------------------------------------------------+
| Argument          | type      | Default   | Description                                         |
+===================+===========+===========+=====================================================+
| model             | Model     | None      | The model. **Required**.                            |
+-------------------+-----------+-----------+-----------------------------------------------------+
| permissions       | Tuple     | None      | The permissions required to access the mutation     |
+-------------------+-----------+-----------+-----------------------------------------------------+
| login\_required   | Boolean   | None      | If true, the calling user has to be authenticated   |
+-------------------+-----------+-----------+-----------------------------------------------------+

.. code::

    mutation {
        deleteUser(id: "VXNlck5vZGU6MQ=="){
            found
            deletedId
        }
    }
