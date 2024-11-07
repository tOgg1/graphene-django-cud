import graphene
from django.test import TestCase
from graphene import Schema

from graphene_django_cud.mutations import DjangoBatchCreateMutation
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Fish
from graphene_django_cud.tests.util import get_introspected_field_kind, get_introspected_list_field_item_kind


class TestBatchCreateMutationRequiredOutputField(TestCase):
    def test__batch_create_mutation_with_required_output_field(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class BatchCreateFishMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Fish
                required_output_field = True

        class Mutations(graphene.ObjectType):
            batch_create_fish = BatchCreateFishMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "BatchCreateFishMutation", "fishs")
        self.assertEqual(field_kind, "NON_NULL")

        field_item_kind = get_introspected_list_field_item_kind(schema, "BatchCreateFishMutation", "fishs")
        self.assertEqual(field_item_kind, "NON_NULL")

    def test__batch_create_mutation_without_required_output_field(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class BatchCreateFishMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Fish
                required_output_field = False

        class Mutations(graphene.ObjectType):
            batch_create_fish = BatchCreateFishMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        field_kind = get_introspected_field_kind(schema, "BatchCreateFishMutation", "fishs")
        self.assertNotEqual(field_kind, "NON_NULL")
