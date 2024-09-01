import graphene
from django.test import TestCase
from graphene_django_cud.util import get_input_fields_for_model
from graphene_django_cud.tests.models import Mouse


class TestGetInputFieldsForModel(TestCase):

    def test__simple_model__returns_correct_fields(self):
        fields = get_input_fields_for_model(
            Mouse,
            ("name", "keeper", "predators"),
            (),
        )

        self.assertEqual(3, len(fields))
        self.assertIn("name", fields)
        self.assertIn("keeper", fields)
        self.assertIn("predators", fields)

        self.assertIsInstance(fields["name"], graphene.String)
        self.assertIsInstance(fields["keeper"], graphene.ID)
        self.assertIsInstance(fields["predators"], graphene.List)

    def test__field_name_mappings__returns_correct_fields(self):
        fields = get_input_fields_for_model(
            Mouse,
            ("name", "keeper", "predators"),
            (),
            field_name_mappings={"keeper": "keeper_id", "predators": "predators_ids"}
        )

        self.assertEqual(3, len(fields))
        self.assertIn("name", fields)
        self.assertIn("keeper_id", fields)
        self.assertIn("predators_ids", fields)
