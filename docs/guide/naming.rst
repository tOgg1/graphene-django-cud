================================
Field, argument and type naming
================================

There are three different names that have to be specified for each mutation:

- The name of the mutation.
- The name of the input argument(s).
- The name of the input argument type.
- The name of the field that can be resolved.

The first one is always set by you, and the second one is always ``input`` or ``id`` (or both).

The two others can be customized by the following meta parameters:

- ``type_name``
- ``return_field_name``

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            type_name = "ChangeUserInput"  # Default here would be UpdateUserInput
            return_field_name = "updatedUser"  # Default here would be user


    class Mutation(graphene.ObjectType):
        update_user = UpdateUserMutation.Field()


.. code::

    mutation UpdateUserMutation($input: ChangeUserInput){
        updateUser(input: $input){
            updatedUser{

            }
        }
    }


Given the existence of `GraphQL aliasing`_, the utility of the latter is questionable.

.. _GraphQL aliasing: https://graphql.org/learn/queries/#aliases
