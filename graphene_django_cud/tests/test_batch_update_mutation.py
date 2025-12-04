import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations.batch_update import DjangoBatchUpdateMutation
from graphene_django_cud.tests.factories import DogFactory, UserFactory, MouseFactory, CatFactory
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Dog, Mouse


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

    def test__use_id_suffixes_for_fk__updates_correct_object(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchUpdateMouseMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Mouse
                use_id_suffixes_for_fk = True

        class Mutations(graphene.ObjectType):
            batch_update_mouse = BatchUpdateMouseMutation.Field()

        user_one = UserFactory.create()
        user_two = UserFactory.create()

        mouse_one = MouseFactory.create(name="Mickey")
        mouse_two = MouseFactory.create(name="Minnie")

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation BatchUpdateMouse(
                $input: [BatchUpdateMouseInput]!
            ){
                batchUpdateMouse(input: $input){
                    mouses{
                        id
                        name
                        keeper{
                            id
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": [
                    {
                        "id": to_global_id("MouseNode", mouse_one.id),
                        "name": "Mickey",
                        "keeperId": to_global_id("UserNode", user_one.id),
                    },
                    {
                        "id": to_global_id("MouseNode", mouse_two.id),
                        "name": "Minnie",
                        "keeperId": to_global_id("UserNode", user_two.id),
                    },
                ]
            },
            context=Dict(user=user_one),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)

        first_mouse = data.batchUpdateMouse.mouses[0]
        second_mouse = data.batchUpdateMouse.mouses[1]

        self.assertEqual("Mickey", first_mouse.name)
        self.assertEqual(to_global_id("UserNode", user_one.id), first_mouse.keeper.id)

        self.assertEqual("Minnie", second_mouse.name)
        self.assertEqual(to_global_id("UserNode", user_two.id), second_mouse.keeper.id)

    def test__use_id_suffixes_for_m2m__updates_correct_object(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchUpdateMouseMutation(DjangoBatchUpdateMutation):
            class Meta:
                model = Mouse
                use_id_suffixes_for_m2m = True

        class Mutations(graphene.ObjectType):
            batch_update_mouse = BatchUpdateMouseMutation.Field()

        user = UserFactory.create()
        mouse_one = MouseFactory.create(name="Mickey", keeper=UserFactory.create())
        mouse_two = MouseFactory.create(name="Minnie", keeper=UserFactory.create())

        cat_one = CatFactory.create()
        cat_two = CatFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation BatchUpdateMouse(
                $input: [BatchUpdateMouseInput]!
            ){
                batchUpdateMouse(input: $input){
                    mouses{
                        id
                        name
                        predators{
                            edges{
                                node{
                                    id
                                }
                            }
                        }
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables={
                "input": [
                    {
                        "id": to_global_id("MouseNode", mouse_one.id),
                        "name": "Mickey",
                        "predatorsIds": [to_global_id("CatNode", cat_one.id), to_global_id("CatNode", cat_two.id)],
                    },
                    {
                        "id": to_global_id("MouseNode", mouse_two.id),
                        "name": "Minnie",
                        "predatorsIds": [to_global_id("CatNode", cat_two.id)],
                    },
                ]
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)

        first_mouse = data.batchUpdateMouse.mouses[0]
        second_mouse = data.batchUpdateMouse.mouses[1]

        first_mouse_predators = list(map(lambda edge: edge.node, first_mouse.predators.edges))
        self.assertEqual(2, len(first_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_one.id), first_mouse_predators[0].id)
        self.assertEqual(to_global_id("CatNode", cat_two.id), first_mouse_predators[1].id)

        second_mouse_predators = list(map(lambda edge: edge.node, second_mouse.predators.edges))
        self.assertEqual(1, len(second_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_two.id), second_mouse_predators[0].id)
