from django.test import TestCase
from graphql import ResolveInfo

from graphene_django_cud.mutations import DjangoUpdateMutation
from graphene_django_cud.tests.models import User


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
                    model = User

    def test__model_registered__does_not_raise_error(self):
        # This registers the UserNode setting
        from .schema import UserNode
        class UpdateMutation(DjangoUpdateMutation):
            class Meta:
                model = User
