from typing import Optional

import factory
from django.contrib.auth.models import Permission
from django.db import models

from graphene_django_cud.tests.models import User, Cat, Dog, Mouse, DogRegistration


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: "username%d" % n)
    email = factory.Faker("email")


class UserAdminFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: "superusername%d" % n)
    email = factory.Faker("email")
    is_superuser = True
    is_staff = True


def _get_permission_from_string(string: str) -> Optional[Permission]:
    try:
        if "." in string:
            app_label, codename = string.split(".")

            return Permission.objects.get(
                content_type__app_label=app_label, codename=codename
            )
        else:
            return Permission.objects.get(codename=string)
    except models.ObjectDoesNotExist:
        return None


class UserWithPermissionsFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "permissionsusername%d" % n)

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            return

        if isinstance(extracted, str):
            permission = _get_permission_from_string(extracted)
            if permission is not None:
                self.user_permissions.add(_get_permission_from_string(extracted))
        elif hasattr(extracted, "__iter__"):
            for permission_string in extracted:
                if not isinstance(permission_string, str):
                    continue

                permission = _get_permission_from_string(permission_string)
                if permission is not None:
                    self.user_permissions.add(permission)
        else:
            raise ValueError(
                "Invalid variable input for permissions, expected string or iterable"
            )


class CatFactory(factory.DjangoModelFactory):
    class Meta:
        model = Cat

    owner = factory.SubFactory(UserFactory)
    name = "Cat"


class DogFactory(factory.DjangoModelFactory):
    class Meta:
        model = Dog

    owner = factory.SubFactory(UserFactory)
    name = "dog"
    tag = factory.Sequence(lambda n: f"tag-{n}")
    breed = "HUSKY"


class DogRegistrationFactory(factory.DjangoModelFactory):
    class Meta:
        model = DogRegistration
        django_get_or_create = ("dog",)

    dog = factory.SubFactory(DogFactory)
    registration_number = "RegNr."


class MouseFactory(factory.DjangoModelFactory):
    class Meta:
        model = Mouse

    name = "mouse"
