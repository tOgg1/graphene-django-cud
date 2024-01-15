import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations import DjangoDeleteMutation
from graphene_django_cud.tests.factories import (
    UserWithPermissionsFactory,
    CatFactory,
    UserFactory,
    FishFactory,
)
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Cat, Fish
from graphene_django_cud.util import disambiguate_id


class TestDeleteMutation(TestCase):
    def test_mutate__object_exists__deletes_object(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserWithPermissionsFactory.create(permissions=["tests.delete_cat"])
        cat = CatFactory.create()
        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation DeleteCat(
                $id: ID!
            ){
                deleteCat(id: $id){
                    found
                    deletedId
                    deletedRawId
                    deletedInputId
                }
            }
        """
        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("CatNode", cat.id),
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(Cat.objects.filter(id=cat.id).first())
        self.assertTrue(data.deleteCat.found)
        self.assertEqual(cat.id, int(disambiguate_id(data.deleteCat.deletedId)))

    def test_mutate__object_does_not_exist__returns_found_false_and_null_id(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserWithPermissionsFactory.create(permissions=["tests.delete_cat"])
        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation DeleteCat(
                $id: ID!
            ){
                deleteCat(id: $id){
                    found
                    deletedId
                }
            }
        """
        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("CatNode", 1),
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertFalse(data.deleteCat.found)
        self.assertEqual(None, data.deleteCat.deletedId)

    def test_muate__user_misses_permission__fails(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation DeleteCat(
                $id: ID!
            ){
                deleteCat(id: $id){
                    found
                    deletedId
                }
            }
        """
        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("CatNode", cat.id),
                # Notably, owner is omitted
                "input": {"name": "New name"},
            },
            context=Dict(user=user),
        )
        self.assertIsNotNone(result.errors)
        self.assertIn("Not permitted", str(result.errors))

    def test__deleting_a_record_with_uuid_pk__with_pk_as_str(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class DeleteFishMutation(DjangoDeleteMutation):
            class Meta:
                model = Fish

        class Mutations(graphene.ObjectType):
            delete_fish = DeleteFishMutation.Field()

        user = UserFactory.create()
        fish = FishFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation DeleteFish(
                $id: ID!
            ){
                deleteFish(id: $id) {
                    found
                    deletedId
                }
            }
        """

        # Excluded use of `to_global_id` and cast UUID to str to match some
        # real-world mutation scenarios.
        result = schema.execute(
            mutation,
            variables={
                "id": str(fish.id)
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        self.assertEqual(Fish.objects.count(), 0)
