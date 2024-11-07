import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations.batch_patch import DjangoBatchPatchMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Dog


class TestBatchPatchMutation(TestCase):
    def test_mutate__objects_exists__updates(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchPatchDogMutation(DjangoBatchPatchMutation):
            class Meta:
                model = Dog

        class Mutations(graphene.ObjectType):
            batch_patch_dog = BatchPatchDogMutation.Field()

        dog_1 = DogFactory.create()
        dog_2 = DogFactory.create()
        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation BatchPatchDog(
                $input: [BatchPatchDogInput]!
            ){
                batchPatchDog(input: $input){
                    dogs {
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
            context=Dict(user=user),
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


class TestBatchPatchMutationRequiredFields(TestCase):
    def setUp(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class PatchDogMutation(DjangoBatchPatchMutation):
            class Meta:
                model = Dog
                required_fields = ("owner",)

        class Mutations(graphene.ObjectType):
            batch_patch_dog = PatchDogMutation.Field()

        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()
        self.dog1 = DogFactory.create(owner=self.user1)
        self.dog2 = DogFactory.create(owner=self.user2)

        self.user1_id = to_global_id("UserNode", self.user1.id)
        self.user2_id = to_global_id("UserNode", self.user2.id)
        self.dog1_id = to_global_id("DogNode", self.dog1.id)
        self.dog2_id = to_global_id("DogNode", self.dog2.id)

        self.schema = Schema(query=DummyQuery, mutation=Mutations)
        self.mutation = """
            mutation BatchPatchDog(
                $input: [BatchPatchDogInput]!
            ){
                batchPatchDog(input: $input){
                    dogs {
                        id
                    }
                }
            }
        """
        self.context = Dict(user=self.user1)

    def test_required_fields__when_set_and_not_provided__returns_error(self):
        result = self.schema.execute(
            self.mutation,
            variables={
                "id": to_global_id("DogNode", self.dog1.id),
                "input": [
                    {
                        "id": self.dog1_id,
                        "name": "Lassie",
                    },
                    {
                        "id": self.dog2_id,
                        "name": "Richard",
                    },
                ],
            },
            context=self.context,
        )
        self.assertIsNotNone(result.errors)

    def test_required_fields__when_set_and_provided__returns_no_error(self):
        result = self.schema.execute(
            self.mutation,
            variables={
                "input": [
                    {
                        "id": self.dog1_id,
                        "name": "Lassie",
                        "owner": self.user2_id,
                    },
                    {
                        "id": self.dog2_id,
                        "name": "Richard",
                        "owner": self.user1_id,
                    },
                ]
            },
            context=self.context,
        )
        self.assertIsNone(result.errors)

        self.dog1.refresh_from_db()
        self.dog2.refresh_from_db()
        self.assertEqual(self.dog1.owner.id, self.user2.id)
        self.assertEqual(self.dog2.owner.id, self.user1.id)


class TestBatchPatchMutationRequiredOutputField(TestCase):
    def test__patch_mutation_with_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class BatchPatchDogMutation(DjangoBatchPatchMutation):
            class Meta:
                model = Dog
                required_output_field = True

        class Mutations(graphene.ObjectType):
            patch_dog = BatchPatchDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        introspected = schema.introspect()
        introspected_types = introspected.get("__schema", {}).get("types", [])
        introspected_mutation = next(
            filter(lambda t: t.get("name", None) == "BatchPatchDogMutation", introspected_types), {}
        )

        self.assertIsNotNone(introspected_mutation)

        introspected_fields = introspected_mutation.get("fields", [])
        introspected_field = next(filter(lambda f: f.get("name", None) == "dogs", introspected_fields), {})
        introspected_field_type = introspected_field.get("type", {}).get("kind", None)

        self.assertEqual(introspected_field_type, "NON_NULL")

    def test__patch_mutation_without_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class BatchPatchDogMutation(DjangoBatchPatchMutation):
            class Meta:
                model = Dog
                required_output_field = False

        class Mutations(graphene.ObjectType):
            create_fish = BatchPatchDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        introspected = schema.introspect()
        introspected_types = introspected.get("__schema", {}).get("types", [])
        introspected_mutation = next(
            filter(lambda t: t.get("name", None) == "BatchPatchDogMutation", introspected_types), {}
        )

        self.assertIsNotNone(introspected_mutation)

        introspected_fields = introspected_mutation.get("fields", [])
        introspected_field = next(filter(lambda f: f.get("name", None) == "dogs", introspected_fields), {})
        introspected_field_type = introspected_field.get("type", {}).get("kind", None)

        self.assertNotEqual(introspected_field_type, "NON_NULL")
