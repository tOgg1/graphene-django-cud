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
)
from graphene_django_cud.tests.models import Cat
from graphene_django_cud.util import disambiguate_id


class TestDeleteMutation(TestCase):
    def test_mutate__object_exists__deletes_object(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserWithPermissionsFactory.create(permissions=["tests.delete_cat"])
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
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
            variables={"id": to_global_id("CatNode", cat.id),},
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(Cat.objects.filter(id=cat.id).first())
        self.assertTrue(data.deleteCat.found)
        self.assertEqual(cat.id, disambiguate_id(data.deleteCat.deletedId))

    def test_mutate__object_does_not_exist__returns_found_false_and_null_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserWithPermissionsFactory.create(permissions=["tests.delete_cat"])
        schema = Schema(mutation=Mutations)
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
            variables={"id": to_global_id("CatNode", 1),},
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertFalse(data.deleteCat.found)
        self.assertEqual(None, data.deleteCat.deletedId)

    def test_muate__user_misses_permission__fails(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class DeleteCatMutation(DjangoDeleteMutation):
            class Meta:
                model = Cat
                permissions = ("tests.delete_cat",)

        class Mutations(graphene.ObjectType):
            delete_cat = DeleteCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
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
