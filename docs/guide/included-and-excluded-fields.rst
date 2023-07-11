.. _included_and_excluded:

================================
Included and excluded fields
================================

*This section is primarily relevant for create, update and patch mutations.*

Excluded fields
------------------

When the mutation input types are created, all model fields are iterated over, and added to the
input object with the corresponding type. Some fields, such as the ``password`` field of the standard User model,
should in most scenarios be excluded. This can be achieved with the ``exclude_fields`` attribute:


.. code:: python

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            exclude_fields = ("password",)


Only fields
--------------------

In some scenarios, if we have a lot of fields excluded, we might want to supply a list of fields that should be
included, and let all others be excluded. This can be achieved with the ``only_fields`` attribute:


.. code:: python

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            only_fields = ("first_name","last_name","address",)


If both ``only_fields`` and ``exclude_fields`` are supplied, first the fields matching ``only_fields`` are extracted,
and then the fields matching ``exclude_fields`` are removed from this list.
