from django.test import TestCase
from graphql import ResolveInfo

from graphene_django_cud.mutations import DjangoUpdateMutation
from graphene_django_cud.tests.models import FakeModel


def mock_info(context=None):
    return ResolveInfo(
        None,
        None,
        None,
        None,
        schema=None,
        fragments=None,
        root_value=None,
        operation=None,
        variable_values=None,
        context=context,
    )



class TestUpdateMutation(TestCase):

    def test__model_not_registered__raises_error(self):
        with self.assertRaises(Exception):
            class UpdateMutation(DjangoUpdateMutation):
                class Meta:
                    model = FakeModel
