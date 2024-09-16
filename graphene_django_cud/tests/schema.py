import asyncio
import random

import graphene
from asgiref.sync import sync_to_async
from django.dispatch import Signal
from graphene import Node, Schema
from graphene_django import DjangoObjectType, DjangoConnectionField

from graphene_django_cud.mutations import (
    DjangoCreateMutation,
    DjangoPatchMutation,
    DjangoUpdateMutation,
    DjangoDeleteMutation,
    DjangoFilterDeleteMutation,
    DjangoBatchCreateMutation,
)
from graphene_django_cud.mutations.filter_update import DjangoFilterUpdateMutation
from graphene_django_cud.signals import post_create_mutation, post_update_mutation, post_delete_mutation
from graphene_django_cud.subscriptions.create import DjangoCreateSubscription
from graphene_django_cud.subscriptions.delete import DjangoDeleteSubscription
from graphene_django_cud.subscriptions.signal import DjangoSignalSubscription
from graphene_django_cud.subscriptions.update import DjangoUpdateSubscription
from graphene_django_cud.tests.models import (
    User,
    Cat,
    Dog,
    Mouse,
    DogRegistration,
    CatUserRelation,
    Fish,
)


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)


class CatNode(DjangoObjectType):
    class Meta:
        model = Cat
        interfaces = (Node,)


class DogNode(DjangoObjectType):
    class Meta:
        model = Dog
        interfaces = (Node,)


class DogRegistrationNode(DjangoObjectType):
    class Meta:
        model = DogRegistration
        interfaces = (Node,)


class MouseNode(DjangoObjectType):
    class Meta:
        model = Mouse
        interfaces = (Node,)


class CatUserRelationNode(DjangoObjectType):
    class Meta:
        model = CatUserRelation
        interfaces = (Node,)


class FishNode(DjangoObjectType):
    class Meta:
        model = Fish
        interfaces = (Node,)


class Query(graphene.ObjectType):
    user = Node.Field(UserNode)
    cat = Node.Field(CatNode)
    dog = Node.Field(DogNode)
    mice = Node.Field(MouseNode)
    cat_user_relation = Node.Field(CatUserRelationNode)
    fish = Node.Field(FishNode)

    all_users = DjangoConnectionField(UserNode)
    all_cats = DjangoConnectionField(CatNode)
    all_dogs = DjangoConnectionField(DogNode)
    all_mice = DjangoConnectionField(MouseNode)
    all_cat_user_relations = DjangoConnectionField(CatUserRelationNode)
    all_fish = DjangoConnectionField(FishNode)


class CreateUserMutation(DjangoCreateMutation):
    class Meta:
        model = User
        exclude = ("password",)
        many_to_one_extras = {
            "cats": {"exact": {"type": "auto"}},
            "dogs": {
                "add": {
                    "field_types": {"tag": graphene.Int()},
                    "many_to_many_extras": {"friends": {"add": {"type": "CreateMouseInput"}}},
                }
            },
        }


class BatchCreateUserMutation(DjangoBatchCreateMutation):
    class Meta:
        model = User
        use_type_name = "CreateUserInput"
        many_to_one_extras = {"cats": {"exact": {"type": "auto"}}}


class PatchUserMutation(DjangoPatchMutation):
    class Meta:
        model = User
        many_to_one_extras = {
            "cats": {"add": {"type": "auto"}, "update": {"type": "auto"}},
            "dogs": {"add": {"many_to_many_extras": {"friends": {"add": {"type": "CreateMouseInput"}}}}},
        }

    @classmethod
    def mutate(cls, root, info, input, id):
        return super().mutate(root, info, input, id)


class UpdateUserMutation(DjangoUpdateMutation):
    class Meta:
        model = User


class DeleteUserMutation(DjangoDeleteMutation):
    class Meta:
        model = User


class CreateCatMutation(DjangoCreateMutation):
    class Meta:
        model = Cat
        many_to_many_extras = {
            "enemies": {"exact": {"type": "CreateDogInput"}},
            "targets": {"exact": {"type": "CreateMouseInput"}},
        }
        many_to_one_extras = {
            "cat_user_relations": {"add": {"type": "auto"}},
        }
        # foreign_key_extras = {"owner": {"type": "CreateUserInput"}}


class BatchCreateCatMutation(DjangoBatchCreateMutation):
    class Meta:
        model = Cat


class UpdateCatMutation(DjangoUpdateMutation):
    class Meta:
        model = Cat
        many_to_many_extras = {
            "enemies": {
                "add": {
                    "type": "CreateDogInput",
                    "many_to_many_extras": {"friends": {"add": {"type": "CreateMouseInput"}}},
                },
                "remove": True,
                "exact": {"type": "ID"},
            }
        }
        foreign_key_extras = {"owner": {"type": "CreateUserInput"}}


class PatchCatMutation(DjangoPatchMutation):
    class Meta:
        model = Cat
        many_to_many_extras = {
            "enemies": {
                "add": {"type": "CreateDogInput"},
                "add_by_id": {"type": "ID", "operation": "add"},
                "remove": True,
            }
        }


class DeleteCatMutation(DjangoDeleteMutation):
    class Meta:
        model = Cat


class CreateDogMutation(DjangoCreateMutation):
    class Meta:
        model = Dog
        field_types = {"tag": graphene.Int(required=False)}

        many_to_many_extras = {"friends": {"add": {"type": "CreateMouseInput"}}}

    @classmethod
    def handle_tag(cls, value, *args, **kwargs):
        return "Dog-" + str(value)


class PatchDogMutation(DjangoPatchMutation):
    class Meta:
        model = Dog
        field_types = {"tag": graphene.Int(required=False)}
        many_to_many_extras = {
            "enemies": {
                "add": {"type": "CreateCatInput"},
                "remove": True,
                "exact": {"type": "ID"},
            }
        }
        one_to_one_extras = {"registration": {"type": "auto"}}

    @classmethod
    def handle_tag(cls, value, *args, **kwargs):
        return "Dog-" + str(value)


class PatchDogRegistrationMutation(DjangoPatchMutation):
    class Meta:
        model = DogRegistration
        one_to_one_extras = {"dog": {"type": "auto"}}


class UpdateDogMutation(DjangoUpdateMutation):
    class Meta:
        model = Dog


class DeleteDogMutation(DjangoDeleteMutation):
    class Meta:
        model = Dog


class CreateMouseMutation(DjangoCreateMutation):
    class Meta:
        model = Mouse


class PatchMouseMutation(DjangoPatchMutation):
    class Meta:
        model = Mouse


class UpdateMouseMutation(DjangoUpdateMutation):
    class Meta:
        model = Mouse


class DeleteMouseMutation(DjangoDeleteMutation):
    class Meta:
        model = Mouse


class FilterDeleteDogMutation(DjangoFilterDeleteMutation):
    class Meta:
        model = Dog
        filter_fields = ("name", "tag")


class FilterDeleteMouseMutation(DjangoFilterDeleteMutation):
    class Meta:
        model = Mouse
        filter_fields = ("id__in", "name__contains", "friends__owner__first_name")


class FilterUpdateDogMutation(DjangoFilterUpdateMutation):
    class Meta:
        model = Dog
        filter_fields = ("name", "name__startswith")


class CreateFishMutation(DjangoCreateMutation):
    class Meta:
        model = Fish


class UpdateFishMutation(DjangoUpdateMutation):
    class Meta:
        model = Fish


class DeleteFishMutation(DjangoDeleteMutation):
    class Meta:
        model = Fish


test_signal = Signal()


class FireRandomSignal(graphene.Mutation):
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info):
        test_signal.send(sender=cls, value=random.randint(0, 100))

        return cls(ok=True)


class Mutations(graphene.ObjectType):
    create_user = CreateUserMutation.Field()

    batch_create_user = BatchCreateUserMutation.Field()
    patch_user = PatchUserMutation.Field()
    update_user = UpdateUserMutation.Field()
    delete_user = DeleteUserMutation.Field()

    create_dog = CreateDogMutation.Field()
    patch_dog = PatchDogMutation.Field()
    update_dog = UpdateDogMutation.Field()
    delete_dog = DeleteDogMutation.Field()

    patch_dog_registration = PatchDogRegistrationMutation.Field()

    filter_update_dog = FilterUpdateDogMutation.Field()
    filter_delete_dog = FilterDeleteDogMutation.Field()

    batch_create_cat = BatchCreateCatMutation.Field()
    create_cat = CreateCatMutation.Field()
    patch_cat = PatchCatMutation.Field()
    update_cat = UpdateCatMutation.Field()
    delete_cat = DeleteCatMutation.Field()

    create_mouse = CreateMouseMutation.Field()
    patch_mouse = PatchMouseMutation.Field()
    update_mouse = UpdateMouseMutation.Field()
    delete_mouse = DeleteMouseMutation.Field()
    batch_delete_mouse = FilterDeleteMouseMutation.Field()

    create_fish = CreateFishMutation.Field()
    update_fish = UpdateFishMutation.Field()
    delete_fish = DeleteFishMutation.Field(0)

    fire_random_signal = FireRandomSignal.Field()


class FishCreatedSubscription(DjangoCreateSubscription):
    class Meta:
        model = Fish


class CatCreatedSubscription(DjangoCreateSubscription):
    class Meta:
        model = Cat
        signal = post_create_mutation

    # noinspection PyStatementEffect
    @classmethod
    def handle_object_created(cls, sender, instance: Cat, *args, **kwargs):
        cat = Cat.objects.select_related("owner").prefetch_related("enemies").get(pk=instance.pk)

        return cat


class CatUpdatedSubscription(DjangoUpdateSubscription):
    class Meta:
        model = Cat
        signal = post_update_mutation

    # noinspection PyStatementEffect
    @classmethod
    def handle_object_updated(cls, sender, instance: Cat, *args, **kwargs):
        cat = Cat.objects.select_related("owner").prefetch_related("enemies").get(pk=instance.pk)

        return cat


class CatDeletedSubscription(DjangoDeleteSubscription):
    class Meta:
        model = Cat
        signal = post_delete_mutation


class RandomSignalFiredSubscription(DjangoSignalSubscription):
    lets_go = graphene.String()

    @classmethod
    def transform_signal_data(cls, data):
        return {"lets_go": f"go {data.get('value', 0)}"}

    class Meta:
        signal = test_signal


def get_random_fish():
    return random.choice(list(Fish.objects.all()))


def get_random_cat():
    return random.choice(list(Cat.objects.all()))


class Subscription(graphene.ObjectType):
    fish_created = FishCreatedSubscription.Field()
    cat_created = CatCreatedSubscription.Field()

    cat_updated = CatUpdatedSubscription.Field()

    cat_deleted = CatDeletedSubscription.Field()
    test_signal_fired = RandomSignalFiredSubscription.Field()


schema = Schema(query=Query, mutation=Mutations, subscription=Subscription)
