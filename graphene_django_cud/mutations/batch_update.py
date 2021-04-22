from collections import OrderedDict
from typing import Iterable

import graphene
from django.db import transaction
from graphene import InputObjectType
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError

from graphene_django_cud.mutations.core import DjangoCudBase, DjangoCudBaseOptions
from graphene_django_cud.registry import get_type_meta_registry
from graphene_django_cud.util import get_input_fields_for_model


class DjangoBatchUpdateMutationOptions(DjangoCudBaseOptions):
    use_type_name = None


class DjangoBatchUpdateMutation(DjangoCudBase):
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
        optional_fields=(),
        required_fields=(),
        auto_context_fields={},
        return_field_name=None,
        many_to_many_extras=None,
        foreign_key_extras=None,
        many_to_one_extras=None,
        one_to_one_extras=None,
        type_name=None,
        use_type_name=None,
        field_types=None,
        custom_fields=None,
        **kwargs,
    ):
        registry = get_global_registry()
        meta_registry = get_type_meta_registry()
        model_type = registry.get_type_for_model(model)

        if auto_context_fields is None:
            auto_context_fields = {}

        if many_to_one_extras is None:
            many_to_one_extras = {}

        if foreign_key_extras is None:
            foreign_key_extras = {}

        if many_to_many_extras is None:
            many_to_many_extras = {}

        if one_to_one_extras is None:
            one_to_one_extras = {}

        if custom_fields is None:
            custom_fields = {}

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            # Pluralize
            return_field_name = to_snake_case(model.__name__) + "s"

        if use_type_name:
            input_type_name = use_type_name
            InputType = registry.get_converted_field(input_type_name)
            if not InputType:
                raise GraphQLError(
                    f"Could not find input type with name {input_type_name}"
                )
        else:
            input_type_name = type_name or f"BatchUpdate{model.__name__}Input"

            model_fields = get_input_fields_for_model(
                model,
                only_fields,
                exclude_fields,
                tuple(auto_context_fields.keys()) + optional_fields,
                required_fields,
                many_to_many_extras,
                foreign_key_extras,
                many_to_one_extras,
                one_to_one_extras=one_to_one_extras,
                parent_type_name=input_type_name,
                field_types=field_types,
                ignore_primary_key=False,
            )

            for name, field in custom_fields.items():
                model_fields[name] = field

            InputType = type(input_type_name, (InputObjectType,), model_fields)

            # Register meta-data
            meta_registry.register(
                input_type_name,
                {
                    "auto_context_fields": auto_context_fields or {},
                    "optional_fields": optional_fields,
                    "required_fields": required_fields,
                    "many_to_many_extras": many_to_many_extras,
                    "many_to_one_extras": many_to_one_extras,
                    "foreign_key_extras": foreign_key_extras,
                    "one_to_one_extras": one_to_one_extras,
                    "field_types": field_types or {},
                },
            )

            registry.register_converted_field(input_type_name, InputType)

        arguments = OrderedDict(input=graphene.List(InputType, required=True))

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.List(model_type)

        if _meta is None:
            _meta = DjangoBatchUpdateMutationOptions(cls)

        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.optional_fields = optional_fields
        _meta.required_fields = required_fields
        _meta.permissions = permissions
        _meta.auto_context_fields = auto_context_fields
        _meta.many_to_many_extras = many_to_many_extras
        _meta.foreign_key_extras = foreign_key_extras
        _meta.many_to_one_extras = many_to_one_extras
        _meta.one_to_one_extras = one_to_one_extras

        _meta.field_types = field_types or {}
        _meta.InputType = InputType
        _meta.input_type_name = input_type_name
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
    def before_save(cls, root, info, input, updated_objects):
        return super().before_save(root, info, input, updated_objects)

    @classmethod
    def after_mutate(cls, root, info, input, updated_objs, return_data):
        return super().after_mutate(root, info, input, updated_objs, return_data)

    @classmethod
    def after_update_obj(cls, root, info, input, obj, full_input):
        return None

    @classmethod
    def validate(cls, root, info, input, full_input):
        return super().validate(root, info, input, full_input)

    @classmethod
    def get_object(cls, root, info, input, full_input):
        return cls.get_queryset(root, info, full_input).get(
            pk=cls.resolve_id(input["id"])
        )

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
        auto_context_fields = cls._meta.auto_context_fields or {}

        updated_objs = []

        with transaction.atomic():
            for data in input:
                cls.validate(root, info, data, input)
                obj = cls.get_object(root, info, data, input)

                obj = cls.update_obj(
                    obj,
                    data,
                    info,
                    auto_context_fields,
                    cls._meta.many_to_many_extras,
                    cls._meta.foreign_key_extras,
                    cls._meta.many_to_one_extras,
                    cls._meta.one_to_one_extras,
                    Model,
                )

                new_obj = cls.after_update_obj(root, info, data, obj, input)

                if new_obj is not None:
                    obj = new_obj

                updated_objs.append(obj)

            before_save_updated_objs = cls.before_save(root, info, input, updated_objs)
            if before_save_updated_objs:
                updated_objs = before_save_updated_objs

            for obj in updated_objs:
                obj.save()

        return_data = {cls._meta.return_field_name: updated_objs}
        cls.after_mutate(root, info, input, updated_objs, return_data)
        return cls(**return_data)
