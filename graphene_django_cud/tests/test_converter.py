import graphene
from django.db import models
from django.test import TestCase

from graphene_django_cud.converter import convert_choices_field


class TestConvertChoicesField(TestCase):
    def test__field_with_choices__is_converted_to_enum(self):
        class MockModel(models.Model):
            field_with_choices = models.CharField(
                max_length=16,
                choices=(
                    ("A", "Choice a"),
                    ("B", "Choice b"),
                    ("C", "Choice c"),
                )
            )

        field = MockModel._meta.get_field("field_with_choices")
        result = convert_choices_field(
            field,
            field.choices
        )

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), True)


    def test__field_has_default__required_is_set_appropriately(self):
        class MockModel(models.Model):
            field_with_choices = models.CharField(
                max_length=16,
                choices=(
                    ("A", "Choice a"),
                    ("B", "Choice b"),
                    ("C", "Choice c"),
                ),
                default="A"
            )

        field = MockModel._meta.get_field("field_with_choices")
        result = convert_choices_field(
            field,
            field.choices
        )

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), False)

