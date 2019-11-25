==============================
Custom field value handling
==============================

Handlers
------------------------------
In some scenarios, field values have to be handled or transformed in a custom manner before it is saved.
For this we can use custom field handlers. To create a custom field handler, add a method to the mutation
class named `handle_<fieldname>`.

Suppose we have a user object with a gpa-score field, which we don't bother to validate, but want to clamp between 1.0 and 4.0.

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User

        @classmethod
        def handle_gpa(cls, value, name, info) -> int:
            return max(1.0, min(4.0, value))

The returned value from a handle-method will be the one used when updating/creating an instance of the model.

Notably, this method will override a few specific internal mechanisms:

- By default, foreign keys fields will have "_id" attached as a suffix to the field name before saving the raw id. Also global relay ids and regular ids are disambiguated.
- Many to many fields which accept IDs are disambiguated in a similar manner.

This will not happen if you add handle-functions for such fields, and hence you are expected to translate the values into values Django understands internally.

**NB: The method signature of handle-fields are due to change before version 1.0.0. The new signature will
most likely be** ``(root, info, value, input)``, with ``obj``, ``id`` and ``full_input`` **as potential extra kwargs.**

Known limitations
----------------------
There is currently no way to separately handle nested fields, beyond handling the entire field substructure. I.e. for a
deeply nested field named ``enemies``, the only way to handle this field and its "sub"-fields, is by having a method
``handle_enemies``.

Do note however, that if models have clashing field names, the handle-method will be called for both these fields.

This is something being actively worked on resolving.
