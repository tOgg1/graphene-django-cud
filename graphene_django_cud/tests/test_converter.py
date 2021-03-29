import graphene
from django.db import models
from django.test import TestCase
from graphene_django.registry import get_global_registry

from graphene_django_cud.converter import convert_choices_field, convert_django_field_with_choices, convert_django_field_to_input


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


class TestConvertDjangoFieldToInput(TestCase):
    def test__decimal_field__is_converted_to_graphene_decimal(self):
        class MockModel(models.Model):
            percent = models.DecimalField(
                max_digits=6,
                decimal_places=3,
                default="100.0",
            )

        field = MockModel._meta.get_field("percent")
        result = convert_django_field_to_input(field)

        self.assertIsInstance(result, graphene.types.Decimal)
        self.assertEqual(result.kwargs.get("required"), False)


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

    # Exists to address: https://github.com/tOgg1/graphene-django-cud/issues/5
    def test_choices_field__choice_field_in_different_locations__accepts_different_parameters(self):
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

    # Exists to adress: https://github.com/tOgg1/graphene-django-cud/issues/9
    def test__one_to_one_field__is_properly_converted(self):

        class MockSuperModel(models.Model):
            name = models.CharField(max_length=128, default="Heidi Klum")

        class MockModel(models.Model):
            super_model = models.OneToOneField(MockSuperModel, on_delete=models.CASCADE, related_name='modelling')  # Model-ling... Get it? xD

        # Convert primary relation
        registry = get_global_registry()
        field = MockModel._meta.get_field("super_model")
        result = convert_django_field_with_choices(
            field,
            registry=registry
        )

        self.assertIsInstance(result, graphene.types.ID)
        self.assertEqual(result.kwargs.get("required"), True)

        # Convert backward relation
        field = MockSuperModel._meta.get_field("modelling")
        result = convert_django_field_with_choices(
            field,
            registry=registry
        )

        self.assertIsInstance(result, graphene.types.ID)
