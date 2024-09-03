.. _field_name_mappings:

================================
Field name mappings
================================

*This feature is currently not implemented for DjangoFilterUpdateMutation.*

Regular field name mappings
------------------------------------

Field mappings are used to rename model fields when creating the associated input fields. For instance,
say you have a model with a field called "full_name", but you want it to be named "name" in the mutation
input variables. You can achieve this by adding a `field name mapping` to the mutation:

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            field_name_mappings = {"full_name": "name"}

The field name mappings are also available for `many_to_many_extras`, `many_to_one_extras` and `foreign_key_extras` arguments.

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            many_to_one_extras = {
                "cats": {
                    "exact": {
                        "type": "auto",
                        "field_name_mappings": {"full_name": "name"}
                    }
                }
            }

This will rename the field "full_name" to "name" in the input type for the "cats" relationship.


Foreign key id suffixes and many to many id suffixes
------------------------------------------------------
Two mappings have specialized handling, namely adding an "_id" suffix to foreign key fields, and and "_ids" suffix
to many to many fields. They can be enabled by adding the following flags respectively:

* `use_id_suffixes_for_fk`
* `use_id_suffixes_for_m2m`

Having "id"/"ids" suffixes in APIs is a common pattern, and hence we have a special flag to enable this behaviour.

You can also enable these fields globally by adding the following to your settings:

.. code:: python

    GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_FK = True # / False, defaults to False
    GRAPHENE_DJANGO_CUD_USE_ID_SUFFIXES_FOR_M2M = True # / False, defaults to False


Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    class User(models.Model):
        name = models.CharField(max_length=255)
        address = models.TextField()


    class Dog(models.Model):
        owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dogs")
        name = models.TextField()


    class Cat(models.Model):
        owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cats")
        name = models.TextField()
        enemies = models.ManyToManyField(Dog, blank=True, related_name="enemies")

    class UserNode(DjangoObjectType):
        class Meta:
            model = User
            interfaces = (Node,)

    class CatNode(DjangoObjectType):
        class Meta:
            model = Cat
            interfaces = (Node,)

    class DogNode(DjangoObjectType):
        class Meta:
            model = Dog
            interfaces = (Node,)
            use_id_suffixes_for_m2m = True


    class CreateDogMutation(DjangoCreateMutation):
        class Meta:
            model = Dog
            interfaces = (Node,)
            use_id_suffixes_for_m2m = True
            use_id_suffixes_for_fk = True


    class Mutation(graphene.ObjectType):
        create_dog = CreateDogMutation.Field()


.. code::

    mutation{
        createDog(input: {name: "Sparky", ownerId: "1", enemiesIds: ["2", "3"]}){
            dog{
                id
                name
                owner{
                    id
                    name
                }
            }
        }
    }
