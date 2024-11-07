import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations.batch_update import DjangoBatchUpdateMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Dog
from graphene_django_cud.tests.util import get_introspected_field_kind, get_introspected_list_field_item_kind


class TestBatchUpdateMutation(TestCase):
    def test_mutate__objects_exists__updates(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchUpdateDogMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Dog

        class Mutations(graphene.ObjectType):
            batch_update_dog = BatchUpdateDogMutation.Field()

        dog_1 = DogFactory.create()
        dog_2 = DogFactory.create()
        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
            context=Dict(user=user),
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


class TestBatchUpdateMutationRequiredOutputField(TestCase):
    def test__patch_mutation_with_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class BatchUpdateDogMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Dog
                required_output_field = True

        class Mutations(graphene.ObjectType):
            batch_update_dog = BatchUpdateDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "BatchUpdateDogMutation", "dogs")
        self.assertEqual(field_kind, "NON_NULL")

        field_item_kind = get_introspected_list_field_item_kind(schema, "BatchUpdateDogMutation", "dogs")
        self.assertEqual(field_item_kind, "NON_NULL")

    def test__patch_mutation_without_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class BatchUpdateDogMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Dog
                required_output_field = False

        class Mutations(graphene.ObjectType):
            batch_update_dog = BatchUpdateDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "BatchUpdateDogMutation", "dogs")
        self.assertNotEqual(field_kind, "NON_NULL")
