from django.db import models


class FakeModel(models.Model):
    char_field = models.CharField(max_length=16)
    num_field = models.IntegerField()
