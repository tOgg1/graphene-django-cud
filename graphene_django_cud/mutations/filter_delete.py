from collections import OrderedDict
from typing import Iterable

import graphene
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from graphene import InputObjectType
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene_django.registry import get_global_registry
from graphql import GraphQLError
from graphql_relay import to_global_id

from graphene_django_cud.mutations.core import DjangoCudBase
from graphene_django_cud.util import get_filter_fields_input_args


class DjangoFilterDeleteMutationOptions(MutationOptions):
    model = None
    filter_fields = None
    filter_class = None
    permissions = None
    login_required = None


class DjangoFilterDeleteMutation(DjangoCudBase):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        _meta=None,
        model=None,
        permissions=None,
        login_required=None,
        filter_fields=(),
        filter_class=None,
        **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        assert model_type, f"Model type must be registered for model {model}"
        assert (
            len(filter_fields) > 0
        ), f"You must specify at least one field to filter on for deletion."

        input_arguments = get_filter_fields_input_args(filter_fields, model)

        InputType = type(
            f"BatchDelete{model.__name__}Input", (InputObjectType,), input_arguments
        )

        arguments = OrderedDict(input=InputType(required=True))

        output_fields = OrderedDict()
        output_fields["deletion_count"] = graphene.Int()
        output_fields["deleted_ids"] = graphene.List(graphene.ID)

        if _meta is None:
            _meta = DjangoFilterDeleteMutationOptions(cls)

        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.filter_fields = filter_fields
        _meta.permissions = permissions
        _meta.login_required = login_required or (
            _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def get_queryset(cls, root, info, input):
        Model = cls._meta.model
        return Model.objects

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
    def before_save(cls, root, info, filter_qs):
        return super().before_save(root, info, filter_qs)

    @classmethod
    def after_mutate(cls, root, info, deletion_count, ids):
        return super().after_mutate(root, info, deletion_count, ids)

    @classmethod
    def validate(cls, root, info, input, id, obj):
        return super().validate(root, info, input)

    @classmethod
    def mutate(cls, root, info, input):
        updated_input = cls.before_mutate(root, info, input)

        if updated_input:
            input = updated_input

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, input)

        Model = cls._meta.model
        model_field_values = {}

        for name, value in super(type(input), input).items():
            filter_field_split = name.split("__", 1)
            field_name = filter_field_split[0]

            try:
                field = Model._meta.get_field(field_name)
            except FieldDoesNotExist:
                # This can happen with nested selectors. In this case we set the field to none.
                field = None

            filter_field_is_list = False

            if len(filter_field_split) > 1:
                # If we have an "__in" final part of the filter, we are now dealing with
                # a list of things. Note that all other variants can be coerced directly
                # on the filter-call, so we don't really have to deal with other cases.
                filter_field_is_list = filter_field_split[-1] == "in"

            new_value = value

            value_handle_name = "handle_" + name
            if hasattr(cls, value_handle_name):
                handle_func = getattr(cls, value_handle_name)
                assert callable(
                    handle_func
                ), f"Property {value_handle_name} on {cls.__name__} is not a function."
                new_value = handle_func(value, name, info)

            # On some fields we perform some default conversion, if the value was not transformed above.
            if new_value == value and value is not None:
                if type(field) in (models.ForeignKey, models.OneToOneField):
                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = cls.resolve_id(value)
                elif (
                    type(field)
                    in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                    )
                    or filter_field_is_list
                ):
                    new_value = cls.resolve_ids(value)

            model_field_values[name] = new_value

        filter_qs = cls.get_queryset(root, info, input).filter(**model_field_values)
        updated_qs = cls.before_save(root, info, filter_qs)

        if updated_qs:
            filter_qs = updated_qs

        ids = [
            to_global_id(get_global_registry().get_type_for_model(Model).__name__, id)
            for id in filter_qs.values_list("id", flat=True)
        ]

        deletion_count, _ = filter_qs.delete()

        cls.after_mutate(root, info, deletion_count, ids)

        return cls(deletion_count=deletion_count, deleted_ids=ids)
