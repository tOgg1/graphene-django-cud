import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema
from graphql import ResolveInfo
from graphql_relay import to_global_id

from graphene_django_cud.mutations import DjangoUpdateMutation, DjangoCreateMutation
from graphene_django_cud.tests.factories import (
    UserFactory,
    CatFactory,
    UserWithPermissionsFactory,
    DogFactory,
    MouseFactory,
)
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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

    def test_get_permissions__list_with_permissions__requires_returned_permissions(
        self,
    ):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

            @classmethod
            def get_permissions(cls, root, info, *args, **kwargs):
                return ["tests.change_cat"]

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create()
        user_with_permissions = UserWithPermissionsFactory.create(
            permissions=["tests.change_cat"]
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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user_with_permissions),
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
            def get_permissions(cls, root, info, input, id, *args, **kwargs):
                owner_id = int(disambiguate_id(input["owner"]))
                if info.context.user.id == owner_id:
                    return []

                return ["tests.change_cat"]

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", new_cat_owner.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Name",
                    "owner": to_global_id("UserNode", new_cat_owner.id),
                },
            },
            context=Dict(user=new_cat_owner),
        )
        self.assertIsNone(result.errors)

    def test_check_permissions__override__uses_new_check_permissions_to_grant_access(
        self,
    ):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                # This will be overridden
                permissions = ("tests.change_cat",)

            @classmethod
            def check_permissions(cls, root, info, input, id, obj) -> None:
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
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {"name": "Name 2", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)
        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {"name": "Name 3", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
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
            def validate_name(cls, root, info, value, input, id, obj):
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
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
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
            def validate_name(cls, root, info, value, input, id, obj):
                owner = User.objects.get(pk=disambiguate_id(input["owner"]))
                if value == owner.get_full_name():
                    raise ValueError("Cat must have different name than owner")

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        user = UserFactory.create(first_name="John", last_name="Doe")
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
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "name": "John Doe",
                    "owner": to_global_id("UserNode", user.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {"name": "Kitty", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

    def test_field_types__specified__overrides_field_type(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                field_types = {"tag": graphene.Int()}

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
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "not-an-int",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "breed": "HUSKY",
                    "tag": 25,
                    "owner": to_global_id("UserNode", user.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)


class TestUpdateMutationManyToManyOnReverseField(TestCase):
    def test_default_setup__adding_resource_by_id__adds_resource(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()
        dog = DogFactory.create()

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [to_global_id("DogNode", dog.id)],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 1)

    def test_default_setup__calling_with_empty_list__resets_relation(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()

        # Create some enemies
        dog = DogFactory.create_batch(5)
        cat.enemies.set(dog)
        self.assertEqual(cat.enemies.all().count(), 5)

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 0)

    def test_many_to_many_extras__calling_exact_with_empty_list__resets_relation(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                many_to_many_extras = {"enemies": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()

        # Create some enemies
        dog = DogFactory.create_batch(5)
        cat.enemies.set(dog)
        self.assertEqual(cat.enemies.all().count(), 5)

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 0)

    def test_many_to_many_extras__add_extra_by_id__adds_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                many_to_many_extras = {"enemies": {"add": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()

        # Create some enemies
        dog = DogFactory.create_batch(5)
        self.assertEqual(cat.enemies.all().count(), 0)

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemiesAdd": [dog.id for dog in dog],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 5)

    def test_many_to_many_extras__add_extra_by_input__adds_by_input(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateDogMutation(DjangoCreateMutation):
            class Meta:
                model = Dog

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                many_to_many_extras = {"enemies": {"exact": {"type": "CreateDogInput"}}}

        class Mutations(graphene.ObjectType):
            create_dog = CreateDogMutation.Field()
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()

        # Create some enemies
        dog = DogFactory.create_batch(5)
        self.assertEqual(cat.enemies.all().count(), 0)

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [
                        {
                            "name": dog.name,
                            "breed": dog.breed,
                            "tag": dog.tag + "-new",
                            "owner": dog.owner.id,
                        }
                        for dog in dog
                    ],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 5)

    def test_many_to_many_extras__remove_extra_by_id__removes_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateCatMutation(DjangoUpdateMutation):
            class Meta:
                model = Cat
                many_to_many_extras = {"enemies": {"remove": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_cat = UpdateCatMutation.Field()

        cat = CatFactory.create()
        user = UserFactory.create()

        # Create some enemies
        dog = DogFactory.create_batch(5)
        cat.enemies.set(dog)
        self.assertEqual(cat.enemies.all().count(), 5)

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
            variables={
                "id": to_global_id("CatNode", cat.id),
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", user.id),
                    "enemiesRemove": [dog.id for dog in dog],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        cat.refresh_from_db()
        self.assertEqual(cat.enemies.all().count(), 0)


class TestUpdateMutationManyToManyExtras(TestCase):
    def test_many_to_many_extras__calling_exact_with_empty_list__resets_relation(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                many_to_many_extras = {"enemies": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        dog.enemies.set(cats)
        self.assertEqual(dog.enemies.all().count(), 5)

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(dog.enemies.all().count(), 0)

    def test_many_to_many_extras__add_extra_by_id__adds_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                many_to_many_extras = {"enemies": {"add": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        self.assertEqual(dog.enemies.all().count(), 0)

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                    "enemiesAdd": [cat.id for cat in cats],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(dog.enemies.all().count(), 5)

    def test_many_to_many_extras__add_extra_by_input__adds_by_input(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateCatMutation(DjangoCreateMutation):
            class Meta:
                model = Cat

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                many_to_many_extras = {"enemies": {"exact": {"type": "CreateCatInput"}}}

        class Mutations(graphene.ObjectType):
            create_cat = CreateCatMutation.Field()
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        self.assertEqual(dog.enemies.all().count(), 0)

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                    "enemies": [
                        {"name": cat.name, "owner": cat.owner.id} for cat in cats
                    ],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(dog.enemies.all().count(), 5)

    def test_many_to_many_extras__remove_extra_by_id__removes_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                many_to_many_extras = {"enemies": {"remove": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        dog.enemies.set(cats)
        self.assertEqual(dog.enemies.all().count(), 5)

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                    "enemiesRemove": [cat.id for cat in cats],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(dog.enemies.all().count(), 0)

    def test_many_to_many_extras__type_auto__makes_it_possible_to_add_new_full_objects(
        self,
    ):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                many_to_many_extras = {"enemies": {"add": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        self.assertEqual(dog.enemies.all().count(), 0)

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                    "enemiesAdd": [
                        {
                            "name": "Meowington",
                            "owner": to_global_id("UserNode", user.id),
                        }
                    ],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(dog.enemies.all().count(), 1)


class TestUpdateMutationManyToOneExtras(TestCase):
    def test_many_to_one_extras__auto_calling_mutation_with_setting_field__does_nothing(
        self,
    ):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        self.assertEqual(user.cats.all().count(), 0)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 0)

    def test_many_to_one_extras__calling_exact_with_empty_list__resets_relation(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5, owner=user)
        self.assertEqual(user.cats.all().count(), 5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "cats": [],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 0)

    def test_many_to_one_extras__set_exact_by_id__sets_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        self.assertEqual(user.cats.all().count(), 0)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "cats": [cat.id for cat in cats],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 5)

    def test_many_to_one_extras__add_by_id__adds_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5, owner=user)
        other_cats = CatFactory.create_batch(5)
        self.assertEqual(user.cats.all().count(), 5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "catsAdd": [cat.id for cat in other_cats],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 10)

    def test_many_to_one_extras__add_by_input__adds_by_input(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateCatMutation(DjangoCreateMutation):
            class Meta:
                model = Cat

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            create_cat = CreateCatMutation.Field()
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some cats
        self.assertEqual(user.cats.all().count(), 0)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "catsAdd": [{"name": "Cat damon"} for _ in range(5)],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 5)

    def test_many_to_one_extras__remove_extra_by_id__removes_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"remove": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some enemies
        cats = CatFactory.create_batch(5)
        user.cats.set(cats)
        self.assertEqual(user.cats.all().count(), 5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "catsRemove": [cat.id for cat in cats],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.cats.all().count(), 0)

    def test_many_to_one_extras__remove_nullable_field__removes_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateUserMutation(DjangoUpdateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"mice": {"remove": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            update_user = UpdateUserMutation.Field()

        user = UserFactory.create()

        # Create some enemies
        mice = MouseFactory.create_batch(5, keeper=user)
        user.mice.set(mice)
        self.assertEqual(user.mice.all().count(), 5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateUser(
                $id: ID!,
                $input: UpdateUserInput! 
            ){
                updateUser(id: $id, input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "miceRemove": [mouse.id for mouse in mice],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        user.refresh_from_db()
        self.assertEqual(user.mice.all().count(), 0)


class TestUpdateMutationForeignKeyExtras(TestCase):
    def test_auto_type__with_proper_setup__generates_new_auto_type(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                foreign_key_extras = {
                    "owner": {"type": "auto", "exclude_fields": ["password"]}
                }

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

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": {
                        "username": "new-user",
                        "email": "new-user@example.com",
                        "firstName": "Tormod",
                        "lastName": "Haugland",
                    },
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual("new-user@example.com", dog.owner.email)


class TestUpdateMutationCustomFields(TestCase):
    def test_custom_field__separate_from_model_fields__adds_new_field_which_can_be_handled(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                custom_fields = {
                    "bark": graphene.Boolean()
                }

            @classmethod
            def before_save(cls, root, info, input, id, obj: Dog):
                if input.get("bark"):
                    obj.bark_count += 1
                return obj

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

        self.assertEqual(0, dog.bark_count)
        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "bark": True,
                    "owner": to_global_id("UserNode", user.id)
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(1, dog.bark_count)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id)
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        dog.refresh_from_db()
        self.assertEqual(1, dog.bark_count)
