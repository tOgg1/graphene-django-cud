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
from graphene_django_cud.tests.models import User, Cat, Dog, DogRegistration
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
                "id": to_global_id("UserNode", user.id),
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
                "id": to_global_id("UserNode", user.id),
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
                "id": to_global_id("UserNode", user.id),
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
                "id": to_global_id("UserNode", user.id),
                "input": {"name": "Name", "owner": to_global_id("UserNode", user.id)},
            },
            context=Dict(user=user),
        )
        self.assertEqual(len(result.errors), 1)

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("UserNode", user.id),
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
                            "tag": dog.tag,
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


class TestCreateMutationManyToOneExtras(TestCase):
    def test_many_to_one_extras__auto_calling_mutation_with_setting_field__does_nothing(
        self,
    ):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateUser(
                $input: CreateUserInput! 
            ){
                createUser(input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                }
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        user = User.objects.get(pk=disambiguate_id(data.createUser.user.id))

        self.assertEqual(user.cats.all().count(), 0)

    def test_many_to_one_extras__set_exact_by_id__sets_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()
        other_cats = CatFactory.create_batch(5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateUser(
                $input: CreateUserInput! 
            ){
                createUser(input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "cats": [cat.id for cat in other_cats],
                }
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        user = User.objects.get(pk=disambiguate_id(data.createUser.user.id))

        self.assertEqual(user.cats.all().count(), 5)

    def test_many_to_one_extras__add_by_id__adds_by_id(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()
        other_cats = CatFactory.create_batch(5)

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateUser(
                $input: CreateUserInput! 
            ){
                createUser(input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "catsAdd": [cat.id for cat in other_cats],
                }
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        user = User.objects.get(pk=disambiguate_id(data.createUser.user.id))

        self.assertEqual(user.cats.all().count(), 5)

    def test_many_to_one_extras__add_by_input__adds_by_input(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateCatMutation(DjangoCreateMutation):
            class Meta:
                model = Cat

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude_fields = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            create_cat = CreateCatMutation.Field()
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateUser(
                $input: CreateUserInput! 
            ){
                createUser(input: $input){
                    user{
                        id
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "catsAdd": [{"name": "Cat Damon"} for _ in range(5)],
                }
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        user = User.objects.get(pk=disambiguate_id(data.createUser.user.id))

        self.assertEqual(user.cats.all().count(), 5)


class TestUpdateWithOneToOneField(TestCase):
    def test__one_to_one_relation_exists__updates_specified_fields(self):

        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogMutation(DjangoUpdateMutation):
            class Meta:
                model = Dog
                one_to_one_extras = {"registration": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            update_dog = UpdateDogMutation.Field()

        user = UserFactory.create()
        dog = DogFactory.create()
        DogRegistration.objects.create(dog=dog, registration_number="1234")

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateDog(
                $id: ID!,
                $input: UpdateDogInput!
            ){
                updateDog(id: $id, input: $input){
                    dog{
                        id
                        registration{
                            id
                            registrationNumber 
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogNode", dog.id),
                "input": {
                    "name": dog.name,
                    "breed": dog.breed,
                    "tag": dog.tag,
                    "owner": to_global_id("UserNode", dog.owner.id),
                    "registration": {"registrationNumber": "12345"},
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(result.errors)
        self.assertEqual("12345", data.updateDog.dog.registration.registrationNumber)

        # Load from database
        dog.refresh_from_db()
        self.assertEqual(dog.registration.registration_number, "12345")

    def test__reverse_one_to_one_exists__updates_specified_fields(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class UpdateDogRegistrationMutation(DjangoUpdateMutation):
            class Meta:
                model = DogRegistration
                one_to_one_extras = {"dog": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            update_dog_registration = UpdateDogRegistrationMutation.Field()

        user = UserFactory.create()
        dog = DogFactory.create(breed="HUSKY")
        dog_registration = DogRegistration.objects.create(
            dog=dog, registration_number="1234"
        )

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation UpdateDogRegistration(
                $id: ID!,
                $input: UpdateDogRegistrationInput!
            ){
                updateDogRegistration(id: $id, input: $input){
                    dogRegistration{
                        id
                        registrationNumber
                        dog{
                            id
                            breed
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "id": to_global_id("DogRegistrationNode", dog_registration.id),
                "input": {
                    "registrationNumber": dog_registration.registration_number,
                    "dog": {
                        "name": dog.name,
                        "breed": "LABRADOR",
                        "tag": dog.tag,
                        "owner": to_global_id("UserNode", dog.owner.id),
                    },
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertEqual(
            "LABRADOR", data.updateDogRegistration.dogRegistration.dog.breed
        )

        # Load from database
        dog_registration.refresh_from_db()
        dog.refresh_from_db()
        self.assertEqual(dog.breed, "LABRADOR")


class TestCreateWithOneToOneField(TestCase):
    def test__one_to_one_relation_exists__creates_specified_fields(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateDogMutation(DjangoCreateMutation):
            class Meta:
                model = Dog
                one_to_one_extras = {"registration": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            create_dog = CreateDogMutation.Field()

        user = UserFactory.create()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateDog(
                $input: CreateDogInput!
            ){
                createDog(input: $input){
                    dog{
                        id
                        registration{
                            id
                            registrationNumber 
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "name": "Sparky",
                    "breed": "HUSKY",
                    "tag": "1234",
                    "owner": to_global_id("UserNode", user.id),
                    "registration": {"registrationNumber": "12345"},
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(result.errors)
        self.assertEqual("12345", data.createDog.dog.registration.registrationNumber)

        # Load from database
        dog = Dog.objects.get(pk=disambiguate_id(data.createDog.dog.id))
        registration = getattr(dog, "registration", None)
        self.assertIsNotNone(registration)
        self.assertEqual(registration.registration_number, "12345")

    def test__reverse_one_to_one_exists__updates_specified_fields(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class CreateDogRegistrationMutation(DjangoCreateMutation):
            class Meta:
                model = DogRegistration
                one_to_one_extras = {"dog": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            create_dog_registration = CreateDogRegistrationMutation.Field()

        user = UserFactory.create()

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation CreateDogRegistration(
                $input: CreateDogRegistrationInput!
            ){
                createDogRegistration(input: $input){
                    dogRegistration{
                        id
                        registrationNumber
                        dog{
                            id
                            name
                            tag
                            breed
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "registrationNumber": "12345",
                    "dog": {
                        "name": "Sparky",
                        "breed": "LABRADOR",
                        "tag": "1234",
                        "owner": user.id,
                    },
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        dog_registration = data.createDogRegistration.dogRegistration
        dog = data.createDogRegistration.dogRegistration.dog

        self.assertEqual("Sparky", dog.name)
        self.assertEqual("LABRADOR", dog.breed)
        self.assertEqual("1234", dog.tag)

        self.assertEqual("12345", dog_registration.registrationNumber)

        # Load from database
        dog_registration = DogRegistration.objects.get(
            pk=disambiguate_id(dog_registration.id)
        )
        dog = getattr(dog_registration, "dog", None)
        self.assertIsNotNone(dog)
        self.assertEqual(dog.name, "Sparky")
        self.assertEqual(dog.tag, "1234")
