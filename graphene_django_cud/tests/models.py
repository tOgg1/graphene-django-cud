import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)


class Mouse(models.Model):
    name = models.TextField()
    keeper = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="mice")


class Cat(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cats")
    name = models.TextField()
    targets = models.ManyToManyField(Mouse, blank=True, related_name="predators")

    user_relations = models.ManyToManyField(User, through="CatUserRelation", blank=True, related_name="related_to_cats")


class Dog(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dogs")
    name = models.TextField()
    tag = models.CharField(
        max_length=16,
        default="Dog-1",
        help_text="Non-unique identifier for the dog, on the form 'Dog-%d'",
    )
    bark_count = models.IntegerField(default=0)
    breed = models.CharField(
        max_length=16,
        choices=(
            ("LABRADOR", "Labrador"),
            ("HUSKY", "Husky"),
            ("BULLDOG", "BULLDOG"),
            ("FLATCOAT", "Flatcoat retriever"),
            ("MALAMUTE", "Alaskan Malamuate"),
        ),
    )

    enemies = models.ManyToManyField(Cat, blank=True, related_name="enemies")
    friends = models.ManyToManyField(Mouse, blank=True, related_name="friends")

    class Meta:
        unique_together = (("owner", "tag"),)


class DogRegistration(models.Model):
    dog = models.OneToOneField(Dog, related_name="registration", on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=32)


class CatUserRelation(models.Model):
    cat = models.ForeignKey(Cat, on_delete=models.CASCADE, related_name="cat_user_relations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cat_user_relations")

    friends = models.BooleanField(default=False)

    class Meta:
        unique_together = (("cat", "user"),)


class Fish(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=40, blank=False, null=False)
