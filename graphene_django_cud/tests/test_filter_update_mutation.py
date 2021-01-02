import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema

from graphene_django_cud.mutations.filter_update import DjangoFilterUpdateMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory
from graphene_django_cud.tests.models import Dog


class TestFilterUpdateMutation(TestCase):
    def test__filter_update__updates(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class FilterUpdateDogMutation(DjangoFilterUpdateMutation):
            class Meta:
                model = Dog
                filter_fields = ("name", "name__startswith")

        class Mutations(graphene.ObjectType):
            filter_update_dogs = FilterUpdateDogMutation.Field()

        dog = DogFactory.create(name="Simen")
        user = UserFactory.create()

        schema = Schema(mutation=Mutations)
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
