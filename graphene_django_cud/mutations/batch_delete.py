from collections import OrderedDict
from typing import Iterable

import graphene
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError
from graphql_relay import to_global_id

from graphene_django_cud.mutations.core import DjangoCudBase


class DjangoBatchDeleteMutationOptions(MutationOptions):
    model = None
    permissions = None
    login_required = None


class DjangoBatchDeleteMutation(DjangoCudBase):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        _meta=None,
        model=None,
        permissions=None,
        login_required=None,
        only_fields=(),
        exclude_fields=(),
        return_field_name=None,
        **kwargs,
    ):
        registry = get_global_registry()

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        arguments = OrderedDict(ids=graphene.List(graphene.ID, required=True))

        output_fields = OrderedDict()
        output_fields["deletion_count"] = graphene.Int()
        output_fields["deleted_ids"] = graphene.List(graphene.ID)
        output_fields["missed_ids"] = graphene.List(graphene.ID)

        if _meta is None:
            _meta = DjangoBatchDeleteMutationOptions(cls)

        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.permissions = permissions
        _meta.login_required = login_required or (
            _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def get_permissions(cls, root, info, input) -> Iterable[str]:
        return super().get_permissions(root, info, input)

    @classmethod
    def check_permissions(cls, root, info, input) -> None:
        return super().check_permissions(root, info, input)

    @classmethod
    def before_mutate(cls, root, info, input):
        return super().before_mutate(root, info, input)

    @classmethod
    def before_save(cls, root, info, qs_to_delete):
        return super().before_save(root, info, qs_to_delete)

    @classmethod
    def after_mutate(cls, root, info, deletion_count, deleted_ids):
        return super().after_mutate(root, info, deletion_count, deleted_ids)

    @classmethod
    def validate(cls, root, info, ids):
        pass

    @classmethod
    def get_queryset(cls, root, info, ids):
        Model = cls._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, ids):
        cls.before_mutate(root, info, ids)

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, ids)

        Model = cls._meta.model
        ids = cls.resolve_ids(ids)

        cls.validate(root, info, ids)

        qs_to_delete = cls.get_queryset(root, info, ids).filter(id__in=ids)

        updated_qs = cls.before_save(root, info, qs_to_delete)

        if updated_qs:
            qs_to_delete = updated_qs

        # Find out which (global) ids are deleted, and which were not found.
        deleted_ids = [
            to_global_id(get_global_registry().get_type_for_model(Model).__name__, id)
            for id in qs_to_delete.values_list("id", flat=True)
        ]

        all_global_ids = [
            to_global_id(get_global_registry().get_type_for_model(Model).__name__, id)
            for id in ids
        ]

        missed_ids = list(
            set(all_global_ids).difference(deleted_ids)
        )

        deletion_count, _ = qs_to_delete.delete()

        cls.after_mutate(root, info, deletion_count, deleted_ids)

        return cls(deletion_count=deletion_count, deleted_ids=deleted_ids, missed_ids=missed_ids)
