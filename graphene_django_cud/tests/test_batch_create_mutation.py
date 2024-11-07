import graphene
from django.test import TestCase
from graphene import Schema

from graphene_django_cud.mutations import DjangoBatchCreateMutation
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.models import Fish


class TestBatchCreateMutationRequiredOutputField(TestCase):
    def test__patch_mutation_with_required_output_field(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class BatchCreateFishMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Fish
                required_output_field = True

        class Mutations(graphene.ObjectType):
            batch_create_fish = BatchCreateFishMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        introspected = schema.introspect()
        introspected_types = introspected.get("__schema", {}).get("types", [])
        introspected_mutation = next(
            filter(lambda t: t.get("name", None) == "BatchCreateFishMutation", introspected_types), {}
        )

        self.assertIsNotNone(introspected_mutation)

        introspected_fields = introspected_mutation.get("fields", [])
        introspected_field = next(filter(lambda f: f.get("name", None) == "fishs", introspected_fields), {})
        introspected_field_type = introspected_field.get("type", {}).get("kind", None)

        self.assertEqual(introspected_field_type, "NON_NULL")

    def test__patch_mutation_without_required_output_field(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class BatchCreateFishMutation(DjangoBatchCreateMutation):
            class Meta:
                model = Fish
                required_output_field = False

        class Mutations(graphene.ObjectType):
            batch_create_fish = BatchCreateFishMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        introspected = schema.introspect()
        introspected_types = introspected.get("__schema", {}).get("types", [])
        introspected_mutation = next(
            filter(lambda t: t.get("name", None) == "BatchCreateFishMutation", introspected_types), {}
        )

        self.assertIsNotNone(introspected_mutation)

        introspected_fields = introspected_mutation.get("fields", [])
        introspected_field = next(filter(lambda f: f.get("name", None) == "fishs", introspected_fields), {})
        introspected_field_type = introspected_field.get("type", {}).get("kind", None)

        self.assertNotEqual(introspected_field_type, "NON_NULL")
