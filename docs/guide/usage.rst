================================
Basic usage
================================

To use, here illustrated by ``DjangoCreateMutation``, simply create a
new inherting class. Suppose we have the following model and Node.

.. code:: python

    class User(models.Model):
        name = models.CharField(max_length=255)
        address = models.TextField()

    class UserNode(DjangoObjectType):
        class Meta:
            model = User
            interfaces = (Node,)

Then we can create a create mutation with the following schema

.. code:: python

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User

    class Mutation(graphene.ObjectType):
        create_user = CreateUserMutation.Field()

    class Query(graphene.ObjectType):
        user = graphene.Field(UserNode, id=graphene.String())

        def resolve_user(self, info, id):
            return User.objects.get(pk=id)

    schema = Schema(query=Query, mutation=Mutation)

Note that the ``UserNode`` has to be registered as a field before the
mutation is instantiated. This will be configurable in the future.

The input to the mutation is a single variable ``input`` which is
automatically created with the models fields. An example mutation would
then be

.. code::

    mutation {
        createUser(input: {name: "John Doe", address: "Downing Street 10"}){
            user{
                id
                name
                address
            }
        }
    }
