import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations import DjangoBatchCreateMutation
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.factories import UserFactory, CatFactory
from graphene_django_cud.tests.models import Mouse


class TestBatchCreateMutation(TestCase):
    def test__calling_batch_create_mutation__creates_objects(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchCreateMouseMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Mouse

        class Mutations(graphene.ObjectType):
            batch_create_mouse = BatchCreateMouseMutation.Field()

        user = UserFactory.create()
        cat_one = CatFactory.create()
        cat_two = CatFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation BatchCreateMouse(
                $input: [BatchCreateMouseInput]!
            ){
                batchCreateMouse(input: $input){
                    mouses{
                        id
                        name
                        keeper{
                            id
                        }
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
                        "name": "Mickey",
                        "keeper": to_global_id("UserNode", user.id),
                        "predators": [to_global_id("CatNode", cat_one.id), to_global_id("CatNode", cat_two.id)],
                    },
                    {
                        "name": "Minnie",
                        "keeper": to_global_id("UserNode", user.id),
                        "predators": [to_global_id("CatNode", cat_one.id), to_global_id("CatNode", cat_two.id)],
                    },
                ]
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)

        first_mouse = data.batchCreateMouse.mouses[0]
        second_mouse = data.batchCreateMouse.mouses[1]

        self.assertEqual("Mickey", first_mouse.name)
        self.assertEqual(to_global_id("UserNode", user.id), first_mouse.keeper.id)
        first_mouse_predators = list(map(lambda edge: edge.node, first_mouse.predators.edges))
        self.assertEqual(2, len(first_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_one.id), first_mouse_predators[0].id)
        self.assertEqual(to_global_id("CatNode", cat_two.id), first_mouse_predators[1].id)

        self.assertEqual("Minnie", second_mouse.name)
        self.assertEqual(to_global_id("UserNode", user.id), second_mouse.keeper.id)
        second_mouse_predators = list(map(lambda edge: edge.node, second_mouse.predators.edges))
        self.assertEqual(2, len(second_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_one.id), second_mouse_predators[0].id)
        self.assertEqual(to_global_id("CatNode", cat_two.id), second_mouse_predators[1].id)

    def test__use_id_suffixes_for_fk__creates_correct_object(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchCreateMouseMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Mouse
                use_id_suffixes_for_fk = True

        class Mutations(graphene.ObjectType):
            batch_create_mouse = BatchCreateMouseMutation.Field()

        user_one = UserFactory.create()
        user_two = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """ 
            mutation BatchCreateMouse( 
                $input: [BatchCreateMouseInput]! 
            ){ 
                batchCreateMouse(input: $input){ 
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
                        "name": "Mickey",
                        "keeperId": to_global_id("UserNode", user_one.id),
                    },
                    {
                        "name": "Minnie",
                        "keeperId": to_global_id("UserNode", user_two.id),
                    },
                ]
            },
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)

        first_mouse = data.batchCreateMouse.mouses[0]
        second_mouse = data.batchCreateMouse.mouses[1]

        self.assertEqual("Mickey", first_mouse.name)
        self.assertEqual(to_global_id("UserNode", user_one.id), first_mouse.keeper.id)

        self.assertEqual("Minnie", second_mouse.name)
        self.assertEqual(to_global_id("UserNode", user_two.id), second_mouse.keeper.id)

    def test__use_id_suffixes_for_m2m__creates_correct_object(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class BatchCreateMouseMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Mouse
                use_id_suffixes_for_m2m = True

        class Mutations(graphene.ObjectType):
            batch_create_mouse = BatchCreateMouseMutation.Field()

        user = UserFactory.create()
        cat_one = CatFactory.create()
        cat_two = CatFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """ 
            mutation BatchCreateMouse( 
                $input: [BatchCreateMouseInput]! 
            ){ 
                batchCreateMouse(input: $input){ 
                    mouses{ 
                        id 
                        name 
                        keeper{ 
                            id 
                        } 
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
                        "name": "Mickey",
                        "keeper": to_global_id("UserNode", user.id),
                        "predatorsIds": [to_global_id("CatNode", cat_one.id), to_global_id("CatNode", cat_two.id)],
                    },
                    {
                        "name": "Minnie",
                        "predatorsIds": [to_global_id("CatNode", cat_two.id)],
                    },
                ]
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)

        first_mouse = data.batchCreateMouse.mouses[0]
        second_mouse = data.batchCreateMouse.mouses[1]

        first_mouse_predators = list(map(lambda edge: edge.node, first_mouse.predators.edges))
        self.assertEqual(2, len(first_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_one.id), first_mouse_predators[0].id)
        self.assertEqual(to_global_id("CatNode", cat_two.id), first_mouse_predators[1].id)

        second_mouse_predators = list(map(lambda edge: edge.node, second_mouse.predators.edges))
        self.assertEqual(1, len(second_mouse_predators))
        self.assertEqual(to_global_id("CatNode", cat_two.id), second_mouse_predators[0].id)
