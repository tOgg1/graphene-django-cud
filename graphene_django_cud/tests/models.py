from django.db import models


class User(models.Model):
    name = models.CharField(max_length=255)


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