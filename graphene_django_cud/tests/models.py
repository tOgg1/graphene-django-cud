from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)


class Mouse(models.Model):
    name = models.TextField()


class Cat(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cats')
    name = models.TextField()
    targets = models.ManyToManyField(
        Mouse,
        blank=True,
        related_name='predators'
    )


class Dog(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dogs')
    name = models.TextField()
    tag = models.CharField(max_length=16, default="Dog-1", help_text="Non-unique identifier for the dog, on the form 'Dog-%d'")

    enemies = models.ManyToManyField(
        Cat,
        blank=True,
        related_name='enemies'
    )
    friends = models.ManyToManyField(
        Mouse,
        blank=True,
        related_name='friends'
    )
