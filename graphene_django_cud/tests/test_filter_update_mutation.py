import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema

from graphene_django_cud.mutations.filter_update import DjangoFilterUpdateMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Dog
from graphene_django_cud.tests.util import get_introspected_field_kind, get_introspected_list_field_item_kind


class TestFilterUpdateMutation(TestCase):
    def test__filter_update__updates(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class FilterUpdateDogMutation(DjangoFilterUpdateMutation):
            class Meta:
                model = Dog
                filter_fields = ("name", "name__startswith")

        class Mutations(graphene.ObjectType):
            filter_update_dogs = FilterUpdateDogMutation.Field()

        dog = DogFactory.create(name="Simen")
        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation FilterUpdateDog(
                $filter: FilterUpdateDogFilterInput!,
                $data: FilterUpdateDogDataInput!
            ){
                filterUpdateDogs(filter: $filter, data: $data){
                    updatedCount
                    updatedObjects{
                        id
                        name
                        tag
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "filter": {"name_Startswith": "Sim"},
                "data": {"tag": "New tag"},
            },
            context=Dict(user=user),
        )

        self.assertIsNone(result.errors)
        self.assertEqual(1, len(result.data["filterUpdateDogs"]["updatedObjects"]))

        dog_result = result.data["filterUpdateDogs"]["updatedObjects"][0]
        self.assertEqual("New tag", dog_result["tag"])

        dog.refresh_from_db()
        self.assertEqual("New tag", dog.tag)


class TestUpdateMutationRequiredOutputField(TestCase):
    def test__update_mutation_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class FilterUpdateDogMutation(DjangoFilterUpdateMutation):
            class Meta:
                model = Dog
                filter_fields = ("name", "name__startswith")
                required_output_field = True

        class Mutations(graphene.ObjectType):
            filter_update_dog = FilterUpdateDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "FilterUpdateDogMutation", "updatedObjects")
        self.assertEqual(field_kind, "NON_NULL")

        field_item_kind = get_introspected_list_field_item_kind(schema, "FilterUpdateDogMutation", "updatedObjects")
        self.assertEqual(field_item_kind, "NON_NULL")

    def test__update_mutation_without_required_output_field(self):
        # This register the DogNode type
        from .schema import DogNode  # noqa: F401

        class FilterUpdateDogMutation(DjangoFilterUpdateMutation):
            class Meta:
                model = Dog
                filter_fields = ("name", "name__startswith")
                required_output_field = False

        class Mutations(graphene.ObjectType):
            filter_update_dog = FilterUpdateDogMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "FilterUpdateDogMutation", "updatedObjects")
        self.assertNotEqual(field_kind, "NON_NULL")
