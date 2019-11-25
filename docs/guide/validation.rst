================================
Field validation
================================

Individual fields
--------------------------------

Before the mutation is executed, the value of each field is validated. By default, each field passes
this validation process. Custom validation can be added per field by adding a ``validate_<fieldname>``-method
to the mutation class.


.. code:: python

    nordic_names = ["Odin", "Tor", "Balder"]

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User

        def validate_first_name(root, info, value, input, **kwargs):
            if not value in nordic_names:
                raise ValueError("First name must be nordic")


Raise an error if a field does not pass validation.

A field validation function always receives the arguments ``(root, info, value, input)``. For some mutations, extra
keyword arguments are also supplied:

- :ref:`DjangoUpdateMutation` and :ref:`DjangoPatchMutation`: ``obj``, the retrieved model instance, and ``id`` the input id.
- :ref:`DjangoBatchCreateMutation`: ``full_input``, the full input object (i.e. containing all objects to be created).


Overriding the validation pipeline
------------------------------------

Internally, each mutation calls a method named `validate`, which in turn finds the individual field validation
methods on the class, and calls these.

You can, however, override this `validate` function, if you need a more complex validation pipeline.


.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User

        @classmethod
        def validate_first_name(cls, root, info, value, input, **kwargs):
            if not value in nordic_names:
                raise ValueError("First name must be nordic")

        @classmethod
        def validate(cls, root, info, input, obj=None, id=None):
            # Check that the user being updated is active
            if obj and obj.is_active == False:
                raise ValueError("Inactive users cannot be updated")

            super().validate(root, info, input, obj=obj, id=id)


The validate method takes the same arguments as the individual validate_field methods, minus the `value` field.


Known limitations
----------------------------

There is currently no way to explicitly validate nested fields, beyond validating the entire field substructure. I.e. for a
deeply nested field named ``enemies``, the only way to validate this field and its "sub"-fields, is by having a method
``validate_enemies``.
