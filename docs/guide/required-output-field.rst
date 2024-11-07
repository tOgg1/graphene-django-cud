.. _required_output_field:

================================
Required output field
================================

*This section is not relevant for delete and batch delete mutations.*

For the below mutation, the type of ``fish`` will by default be ``FishNode``,
meaning it will be nullable.

.. code::

    mutation CreateFish($input: CreateFishInput!) {
      createFish(input: $input) {
        fish {
          id
          name
        }
      }
    }

If you rather want the type to be ``FishNode!`` (non-nullable), you can specify
the required_output_field in the mutation meta, like so:

.. code-block:: python

    class CreateFishMutation(DjangoCreateMutation):
        class Meta:
            model = Fish
            required_output_field = True
