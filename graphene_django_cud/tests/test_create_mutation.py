import graphene
from addict import Dict
from django.test import TestCase
from graphene import ResolveInfo
from graphene import Schema
from graphql_relay import to_global_id

from graphene_django_cud.mutations import DjangoCreateMutation
from graphene_django_cud.tests.dummy_query import DummyQuery
from graphene_django_cud.tests.factories import (
    UserFactory,
    CatFactory,
    DogFactory,
    FishFactory,
)
from graphene_django_cud.tests.models import User, Cat, Dog, DogRegistration, Fish
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


class TestCreateMutationManyToOneExtras(TestCase):
    def test_many_to_one_extras__auto_calling_mutation_with_setting_field__does_nothing(
            self,
    ):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
        from .schema import UserNode  # noqa: F401

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude = ("password",)
                many_to_one_extras = {"cats": {"exact": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()
        other_cats = CatFactory.create_batch(5)

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
        from .schema import UserNode  # noqa: F401

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "ID"}}}

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()
        other_cats = CatFactory.create_batch(5)

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
        from .schema import UserNode  # noqa: F401

        class CreateCatMutation(DjangoCreateMutation):
            class Meta:
                model = Cat

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude = ("password",)
                many_to_one_extras = {"cats": {"add": {"type": "auto"}}}

        class Mutations(graphene.ObjectType):
            create_cat = CreateCatMutation.Field()
            create_user = CreateUserMutation.Field()

        user = UserFactory.build()

        schema = Schema(query=DummyQuery, mutation=Mutations)
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


class TestCreateWithOneToOneField(TestCase):
    def test__one_to_one__without_extra__assigns_field(self):
        # This registers the UserNode type
        from .schema import UserNode

        class CreateDogRegistrationMutation(DjangoCreateMutation):
            class Meta:
                model = DogRegistration

        class Mutations(graphene.ObjectType):
            create_dog_registration = CreateDogRegistrationMutation.Field()

        user = UserFactory.create()
        dog = DogFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)

        mutation = """
            mutation CreateDogRegistration(
                $input: CreateDogRegistrationInput!
            ){
                createDogRegistration(input: $input){
                    dogRegistration{
                        id
                        registrationNumber
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "registrationNumber": "12345",
                    "dog": to_global_id("DogNode", dog.id),
                },
            },
            context=Dict(user=user),
        )

        self.assertIsNone(result.errors)
        data = Dict(result.data)

        self.assertEqual("12345", data.createDogRegistration.dogRegistration.registrationNumber)

        dog_registration = DogRegistration.objects.get(
            pk=disambiguate_id(data.createDogRegistration.dogRegistration.id))
        self.assertEqual(dog_registration.registration_number, "12345")
        dog = getattr(dog_registration, "dog", None)
        self.assertIsNotNone(dog)
        self.assertEqual(dog.id, dog.id)


    def test__one_to_one_relation_exists__creates_specified_fields(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateDogMutation(DjangoCreateMutation):
            class Meta:
                model = Dog
                one_to_one_extras = {"registration": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            create_dog = CreateDogMutation.Field()

        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
        dog.refresh_from_db()
        registration = getattr(dog, "registration", None)
        self.assertIsNotNone(registration)
        self.assertEqual(registration.registration_number, "12345")

    def test__reverse_one_to_one_exists__updates_specified_fields(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateDogRegistrationMutation(DjangoCreateMutation):
            class Meta:
                model = DogRegistration
                one_to_one_extras = {"dog": {"type": "auto"}}

        class Mutations(graphene.ObjectType):
            create_dog_registration = CreateDogRegistrationMutation.Field()

        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
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
        dog_registration = DogRegistration.objects.get(pk=disambiguate_id(dog_registration.id))
        dog = getattr(dog_registration, "dog", None)
        self.assertIsNotNone(dog)
        self.assertEqual(dog.name, "Sparky")
        self.assertEqual(dog.tag, "1234")


class TestCreateWithPlainManyToOneRelation(TestCase):
    def test__many_to_one_relation_exists__creates_specified_fields(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateUserMutation(DjangoCreateMutation):
            class Meta:
                model = User
                exclude = ("password",)

        class Mutations(graphene.ObjectType):
            create_user = CreateUserMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation CreateUser(
                $input: CreateUserInput!
            ){
                createUser(input: $input){
                    user{
                        id
                        cats{
                            edges{
                                node{
                                    id
                                }
                            }
                        }
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "username": "john",
                    "email": "test@example.com",
                    "firstName": "John",
                    "lastName": "Doe",
                    "cats": [to_global_id("CatNode", cat.id)],
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(result.errors)
        self.assertEqual(to_global_id("CatNode", cat.id), data.createUser.user.cats.edges[0].node.id)

        new_user = User.objects.get(pk=disambiguate_id(data.createUser.user.id))

        # Load from database
        cat.refresh_from_db()
        self.assertEqual(cat, new_user.cats.first())


class TestCreateWithPlainManyToManyRelation(TestCase):
    def test__many_to_one_relation_exists__creates_specified_fields(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateDogMutation(DjangoCreateMutation):
            class Meta:
                model = Dog

        class Mutations(graphene.ObjectType):
            create_dog = CreateDogMutation.Field()

        user = UserFactory.create()
        cat = CatFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation CreateDog(
                $input: CreateDogInput!
            ){
                createDog(input: $input){
                    dog{
                        id
                        enemies{
                            edges{
                                node{
                                    id
                                }
                            }
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
                    "enemies": [to_global_id("CatNode", cat.id)],
                },
            },
            context=Dict(user=user),
        )

        self.assertIsNone(result.errors)
        data = Dict(result.data)
        self.assertIsNone(result.errors)
        self.assertEqual(to_global_id("CatNode", cat.id), data.createDog.dog.enemies.edges[0].node.id)

        new_dog = Dog.objects.get(pk=disambiguate_id(data.createDog.dog.id))

        # Load from database
        cat.refresh_from_db()
        self.assertEqual(cat, new_dog.enemies.first())


class TestCreateMutationCustomFields(TestCase):
    def test_custom_field__separate_from_model_fields__adds_new_field_which_can_be_handled(
            self,
    ):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateDogMutation(DjangoCreateMutation):
            class Meta:
                model = Dog
                custom_fields = {"bark": graphene.Boolean()}

            @classmethod
            def before_save(cls, root, info, input, obj):
                if input.get("bark"):
                    obj.bark_count += 1
                return obj

        class Mutations(graphene.ObjectType):
            create_dog = CreateDogMutation.Field()

        dog = DogFactory.create()
        user = UserFactory.create()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation CreateDog(
                $input: CreateDogInput!
            ){
                createDog(input: $input){
                    dog{
                        id
                        barkCount
                    }
                }
            }
        """

        self.assertEqual(0, dog.bark_count)
        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "name": "Sparky",
                    "tag": "tag",
                    "breed": "HUSKY",
                    "bark": True,
                    "owner": to_global_id("UserNode", user.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        self.assertEqual(1, result.data["createDog"]["dog"]["barkCount"])

        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "name": "Sparky",
                    "tag": "tag-2",
                    "breed": "HUSKY",
                    "owner": to_global_id("UserNode", user.id),
                },
            },
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        self.assertEqual(0, result.data["createDog"]["dog"]["barkCount"])


class TestCreateWithManyToManyThroughModel(TestCase):
    def test__creating_a_related_entity_with_a_through_model__works_as_intended(self):
        # This registers the UserNode type
        from .schema import UserNode  # noqa: F401

        class CreateCatMutation(DjangoCreateMutation):
            class Meta:
                model = Cat
                many_to_one_extras = {
                    "cat_user_relations": {
                        "add": {
                            "type": "auto",
                        }
                    }
                }

        owner = UserFactory.create()
        other_user = UserFactory.create()

        class Mutations(graphene.ObjectType):
            create_cat = CreateCatMutation.Field()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation CreateCat(
                $input: CreateCatInput!
            ){
                createCat(input: $input){
                    cat{
                        id
                        catUserRelations{
                            edges{
                                node {
                                    id
                                    friends
                                    user{
                                        id
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        result = schema.execute(
            mutation,
            variables={
                "input": {
                    "name": "Garfield",
                    "owner": to_global_id("UserNode", owner.id),
                    "catUserRelationsAdd": [
                        {
                            "user": to_global_id("UserNode", other_user.id),
                            "friends": True,
                        }
                    ],
                }
            },
        )

        self.assertIsNone(result.errors)
        cat = result.data["createCat"]["cat"]
        self.assertEqual(
            cat["catUserRelations"]["edges"][0]["node"]["user"]["id"],
            to_global_id("UserNode", other_user.id),
        )


class TestCreateUuidPk(TestCase):
    def test__creating_a_record_with_uuid_pk(self):
        # This register the FishNode type
        from .schema import FishNode  # noqa: F401

        class CreateFishMutation(DjangoCreateMutation):
            class Meta:
                model = Fish

        class Mutations(graphene.ObjectType):
            create_fish = CreateFishMutation.Field()

        user = UserFactory.create()
        fish = FishFactory.build()

        schema = Schema(query=DummyQuery, mutation=Mutations)
        mutation = """
            mutation CreateFish(
                $input: CreateFishInput!
            ){
                createFish(input: $input) {
                    fish {
                        id
                        name
                    }
                }
            }
        """

        result = schema.execute(
            mutation,
            variables={"input": {"name": fish.name}},
            context=Dict(user=user),
        )
        self.assertIsNone(result.errors)

        data = Dict(result.data)
        self.assertEqual(data.createFish.fish.name, fish.name)
