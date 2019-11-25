.. _optional_and_excluded:

================================
Optional and required fields
================================

*This section is primarily relevant for create, update and patch mutations.*

General rules
-------------------

There are certain rules which decide whether or not a field is marked as required. For patch mutations, all fields
are always marked as optional. For update and create mutations, however, the following rules apply:

1. If the field has an :ref:`explicit override<explicitly_overriding>`, this is used.
2. If the field has a `default`-value, it is marked as optional.
3. If the field is a many-to-many field and has `blank=True`, it is marked as optional.
4. If the field is nullable, it is marked as optional.
5. In all other scenarios, the field is marked as required.

.. _explicitly_overriding:

Explicitly overriding
------------------------

A field can explicitly be marked as optional or required with the meta-attributes ``optional_fields`` and ``required_fields``:

.. code:: python

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            required_fields = ("first_name",)
            optional_fields = ("last_name",)

