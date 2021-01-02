import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations.batch_update import DjangoBatchUpdateMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.models import Dog


class TestBatchUpdateMutation(TestCase):
    def test_mutate__objects_exists__updates(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class BatchUpdateDogMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Dog

        class Mutations(graphene.ObjectType):
            batch_update_dog = BatchUpdateDogMutation.Field()

        dog_1 = DogFactory.create()
        dog_2 = DogFactory.create()
        user = UserFactory.create()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation BatchUpdateDog(
                $input: [BatchUpdateDogInput]! 
            ){
                batchUpdateDog(input: $input){
                    dogs{
                        id
                        name
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": [
                    {
                        "id": to_global_id("DogNode", dog_1.id),
                        "name": "New name 1",
                        "tag": dog_1.tag,
                        "breed": dog_1.breed,
                        "owner": to_global_id("UserNode", dog_1.owner.id),
                    },
                    {
                        "id": to_global_id("DogNode", dog_2.id),
                        "name": "New name 2",
                        "tag": dog_2.tag,
                        "breed": dog_2.breed,
                        "owner": to_global_id("UserNode", dog_2.owner.id),
                    },
                ]
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

        dogs = result.data["batchUpdateDog"]["dogs"]
        dog_1_result = dogs[0]
        dog_2_result = dogs[1]
        self.assertEqual("New name 1", dog_1_result["name"])
        self.assertEqual("New name 2", dog_2_result["name"])

        dog_1.refresh_from_db()
        dog_2.refresh_from_db()
        self.assertEqual("New name 1", dog_1.name)
        self.assertEqual("New name 2", dog_2.name)
