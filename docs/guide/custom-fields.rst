.. _custom_fields:

================================
Custom fields
================================

It is possible to add custom input fields to the following mutations:

 * DjangoCreateMutation
 * DjangoPatchMutation
 * DjangoUpdateMutation
 * DjangoBatchCreateMutation
 * DjangoBatchPatchMutation
 * DjangoBatchUpdateMutation

The custom fields will be added to the top-level `input` input data structure. While the fields
will not be used directly in any creation/updating process by the library itself, they can be accessed
in all `handle-` and `hook`-methods.


.. code-block:: python

    class Dog(models.Model):
        name = models.TextField()
        bark_count = models.IntegerField(default=0)

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            custom_fields = {
                "bark": graphene.Boolean()
            }

        @classmethod
        def before_save(cls, root, info, input, id, obj: Dog):
            if input.get("bark"):
                obj.bark_count += 1
            return obj


Running the below mutation will increase the bark count by one:

.. code-block::

    updateDog(id: "RG9nTm9kZToxMw==", input: {name: "Sparky", bark: true}){
        dog{
            id
            barkCount
        }
    }

