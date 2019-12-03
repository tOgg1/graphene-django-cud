import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql import ResolveInfo
from graphql_relay import to_global_id

from graphene_django_cud.mutations import DjangoUpdateMutation
from graphene_django_cud.tests.factories import UserFactory, CatFactory, UserWithPermissionsFactory, DogFactory
from graphene_django_cud.tests.models import User, Cat, Dog
from graphene_django_cud.util import disambiguate_id


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
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateMutation(DjangoUpdateMutation):
            class Meta:
                model = User

    def test_permissions__user_has_no_permission__returns_error(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                permissions = ("tests.change_cat",)

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)


    def test_permissions__user_has_permission__does_not_return_error(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                permissions = ("tests.change_cat",)

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserWithPermissionsFactory.create(permissions=["tests.change_cat"])
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

    def test_get_permissions__empty_list__overrides_and_grants_access(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                # This will be overridden
                permissions = ("tests.change_cat",)

            @classmethod
            def get_permissions(cls, root, info, *args, **kwargs):
                return []

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)


    def test_get_permissions__list_with_permissions__requires_returned_permissions(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

            @classmethod
            def get_permissions(cls, root, info, *args, **kwargs):
                return [
                    "tests.change_cat"
                ]

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        user_with_permissions = UserWithPermissionsFactory.create(permissions=["tests.change_cat"])
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user_with_permissions)
        )
        self.assertIsNone(result.errors)

    def test_get_permissions__conditional_list__requires_returned_permissions(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

            @classmethod
            def get_permissions(cls, root, info, id, input, *args, **kwargs):
                owner_id = int(disambiguate_id(input["owner"]))
                if info.context.user.id == owner_id:
                    return []

                return [
                    "tests.change_cat"
                ]

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        new_cat_owner = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", new_cat_owner.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", new_cat_owner.id)
                }
            },
            context=Dict(user=new_cat_owner)
        )
        self.assertIsNone(result.errors)

    def test_check_permissions__override__uses_new_check_permissions_to_grant_access(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                # This will be overridden
                permissions = ("tests.change_cat",)

            @classmethod
            def check_permissions(cls, root, info, id, input) -> None:
                if input["name"] == "Name 2":
                    raise ValueError("Cannot be Name 2")

                return None

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name 2",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name 3",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

    def test_validate__validate_field_does_nothing__passes(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

            @classmethod
            def validate_name(cls, root, info, value, input, **kwargs):
                pass

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

    def test_validate__validate_field_raises__returns_error(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

            @classmethod
            def validate_name(cls, root, info, value, input, **kwargs):
                owner = User.objects.get(pk=disambiguate_id(input["owner"]))
                if value == owner.get_full_name():
                    raise ValueError("Cat must have different name than owner")

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create(
            first_name="John",
            last_name="Doe"
        )
        cat = CatFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateCat(
                $id: ID!,
                $input: UpdateCatInput! 
            ){
                updateCat(id: $id, input: $input){
                    cat{
                        id
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "John Doe",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "Kitty",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

    def test_field_types__specified__overrides_field_type(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                field_types = {
                    "tag": graphene.Int()
                }

            @classmethod
            def handle_tag(self, value, *args, **kwargs):
                return f"Dog-{value}"

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateDog(
                $id: ID!,
                $input: UpdateDogInput! 
            ){
                updateDog(id: $id, input: $input){
                    dog{
                        id
                    }
                }
            }
        """
        # Result with a string in the tag field should fail now
        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "not-an-int",
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables= {
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": 25,
                    "owner": to_global_id("UserNode", user.id)
                }
            },
            context=Dict(user=user)
        )
        self.assertIsNone(result.errors)

