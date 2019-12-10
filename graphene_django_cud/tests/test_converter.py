import graphene
from django.db import models
from django.test import TestCase
from graphene_django.registry import get_global_registry

from graphene_django_cud.converter import convert_choices_field, convert_django_field_with_choices


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
        )(required=True)

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), True)




class ConvertDjangoFieldWithChoices(TestCase):
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
        result = convert_django_field_with_choices(
            field,
        )

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), False)

    def test_choices_field__choice_field_in_different_locations__accepts_different_parameters(self):
        # Exists to address: https://github.com/tOgg1/graphene-django-cud/issues/5
        class MockModel(models.Model):
            field_with_choices = models.CharField(
                max_length=16,
                choices=(
                    ("A", "Choice a"),
                    ("B", "Choice b"),
                    ("C", "Choice c"),
                )
            )

        registry = get_global_registry()
        field = MockModel._meta.get_field("field_with_choices")
        result = convert_django_field_with_choices(
            field,
            registry=registry
        )

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), True)

        result = convert_django_field_with_choices(
            field,
            registry,
            required=False
        )

        self.assertIsInstance(result, graphene.types.Enum)
        self.assertEqual(result.kwargs.get("required"), False)
