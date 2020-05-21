from collections import OrderedDict
from typing import Iterable

import graphene
from django.core.exceptions import ObjectDoesNotExist
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError

from graphene_django_cud.mutations.core import DjangoCudBase
from graphene_django_cud.util import disambiguate_id


class DjangoDeleteMutationOptions(MutationOptions):
    model = None
    permissions = None
    login_required = None


class DjangoDeleteMutation(DjangoCudBase):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
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

        arguments = OrderedDict(id=graphene.ID(required=True))

        output_fields = OrderedDict()
        output_fields["found"] = graphene.Boolean()
        output_fields["deleted_id"] = graphene.ID()

        _meta = DjangoDeleteMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.permissions = permissions
        _meta.login_required = _meta.login_required or (
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
    def before_save(cls, root, info, input, obj):
        return super().before_save(root, info, input, obj)

    @classmethod
    def after_mutate(cls, root, info, deleted_id):
        return super().after_mutate(root, info, deleted_id)

    @classmethod
    def validate(cls, root, info, input):
        return super().validate(root, info, input)

    @classmethod
    def get_queryset(cls, root, info, id):
        Model = cls._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, id):
        cls.before_mutate(root, info, id)

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, id)

        Model = cls._meta.model
        id = disambiguate_id(id)

        try:
            obj = cls.get_queryset(root, info, id).get(pk=id)
            cls.before_save(root, info, obj, id)
            obj.delete()
            cls.after_mutate(root, info, id)
            return cls(found=True, deleted_id=id)
        except ObjectDoesNotExist:
            return cls(found=False)
