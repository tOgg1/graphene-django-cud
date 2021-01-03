# Graphene Django CUD

![Version](https://img.shields.io/pypi/v/graphene-django-cud)
![Build status](https://travis-ci.org/tOgg1/graphene-django-cud.svg?branch=develop)
[![Documentation Status](https://readthedocs.org/projects/graphene-django-cud/badge/?version=latest)](https://graphene-django-cud.readthedocs.io/en/latest/?badge=latest)
![License](https://img.shields.io/github/license/tOgg1/graphene-django-cud)

This package contains a number of helper mutations making it easy to construct create, update and delete mutations for django models.

The helper mutations are:
 * `DjangoCreateMutation`
 * `DjangoPatchMutation`
 * `DjangoUpdateMutation`
 * `DjangoDeleteMutation`
 * `DjangoBatchCreateMutation`
 * `DjangoBatchPatchMutation`
 * `DjangoBatchUpdateMutation`
 * `DjangoBatchDeleteMutation`
 * `DjangoFilterUpdateMutation`
 * `DjangoFilterDeleteMutation`

The package handles both regular ids and relay ids automatically.

## Installation

`pip install graphene_django_cud`

## Basic usage

To use, here illustrated by `DjangoCreateMutation`, simply create a new inherting class.
Suppose we have the following model and Node.

```python
class User(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()

class UserNode(DjangoObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
```

Then we can create a create mutation with the following schema

```python
class CreateUserMutation(DjangoCreateMutation):
    class Meta:
        model = User


class Mutation(graphene.ObjectType):
    create_user = CreateUserMutation.Field()


schema = Schema(mutation=Mutation)
```

Note that the `UserNode` has to be registered as a field before the mutation is instantiated. This will be configurable in the future.

The input to the mutation is a single variable `input` which is automatically created with the models fields.
An example mutation would then be

```graphql
mutation {
    createUser(input: {name: "John Doe", address: "Downing Street 10"}){
        user{
            id
            name
            address
        } 
    }
}
```

## Documentation

The full documentation can be found at https://graphene-django-cud.readthedocs.io/en/latest/.
