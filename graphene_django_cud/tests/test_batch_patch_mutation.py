import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations.batch_patch import DjangoBatchPatchMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.models import Dog


class TestBatchPatchMutation(TestCase):
    def test_mutate__objects_exists__updates(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class BatchPatchDogMutation(DjangoBatchPatchMutation):
            class Meta:
                model = Dog

        class Mutations(graphene.ObjectType):
            batch_patch_dog = BatchPatchDogMutation.Field()

        dog_1 = DogFactory.create()
        dog_2 = DogFactory.create()
        user = UserFactory.create()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation BatchPatchDog(
                $input: [BatchPatchDogInput]! 
            ){
                batchPatchDog(input: $input){
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
                    },
                    {
                        "id": to_global_id("DogNode", dog_2.id),
                        "name": "New name 2",
                    },
                ]
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

        dogs = result.data["batchPatchDog"]["dogs"]
        dog_1_result = dogs[0]
        dog_2_result = dogs[1]
        self.assertEqual("New name 1", dog_1_result["name"])
        self.assertEqual("New name 2", dog_2_result["name"])

        dog_1.refresh_from_db()
        dog_2.refresh_from_db()
        self.assertEqual("New name 1", dog_1.name)
        self.assertEqual("New name 2", dog_2.name)
