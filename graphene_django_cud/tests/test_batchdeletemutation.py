import random

import graphene
from addict import Dict
from django.test import TestCase
from graphene import Schema

from graphene_django_cud.mutations.batch_delete import DjangoBatchDeleteMutation
from graphene_django_cud.tests.factories import UserFactory
from graphene_django_cud.tests.models import User
from graphene_django_cud.util import disambiguate_ids


class TestBatchDeleteMutation(TestCase):
    def test__ids_exist__deletes_relevant_objects(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class BatchDeleteUserMutation(DjangoBatchDeleteMutation):
            class Meta:
                model = User

        class Mutations(graphene.ObjectType):
            batch_delete_user = BatchDeleteUserMutation.Field()

        users = UserFactory.create_batch(10)
        schema = Schema(mutation=Mutations)
        mutation = """
            mutation BatchDeleteUser(
                $ids: [ID]!,
            ){
                batchDeleteUser(ids: $ids){
                    deletedIds
                    missedIds
                    deletionCount
                }
            }
        """

        result = schema.execute(
            mutation, variables={"ids": [user.id for user in users]},
        )
        data = Dict(result.data)
        self.assertEqual(10, data.batchDeleteUser.deletionCount)
        self.assertListEqual(
            list(sorted([str(user.id) for user in users])),
            list(sorted(disambiguate_ids(data.batchDeleteUser.deletedIds))),
        )
        self.assertListEqual([], data.batchDeleteUser.missedIds)

    def test__ids_does_not_exist__only_deletes_relevant_objects(self):
        # This registers the UserNode type
        # noinspection PyUnresolvedReferences
        from .schema import UserNode

        class BatchDeleteUserMutation(DjangoBatchDeleteMutation):
            class Meta:
                model = User

        class Mutations(graphene.ObjectType):
            batch_delete_user = BatchDeleteUserMutation.Field()

        users = UserFactory.create_batch(10)

        selection = random.sample(users, k=5)
        non_existing_ids = list(range(-1, -5))

        ids_to_delete = [user.id for user in selection] + non_existing_ids

        schema = Schema(mutation=Mutations)
        mutation = """
            mutation BatchDeleteUser(
                $ids: [ID]!,
            ){
                batchDeleteUser(ids: $ids){
                    deletedIds
                    missedIds
                    deletionCount
                }
            }
        """

        result = schema.execute(
            mutation, variables={"ids": ids_to_delete},
        )
        data = Dict(result.data)
        self.assertEqual(5, data.batchDeleteUser.deletionCount)
        self.assertListEqual(
            list(sorted([str(user.id) for user in selection])),
            list(sorted(disambiguate_ids(data.batchDeleteUser.deletedIds))),
        )
        self.assertListEqual(
            non_existing_ids,
            list(sorted(disambiguate_ids(data.batchDeleteUser.missedIds))),
        )
