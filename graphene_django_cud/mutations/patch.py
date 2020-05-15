from collections import OrderedDict

import graphene
from django.db import transaction
from graphene import InputObjectType
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError

from graphene_django_cud.mutations.core import DjangoCudBase
from graphene_django_cud.registry import get_type_meta_registry
from graphene_django_cud.util import get_all_optional_input_fields_for_model, disambiguate_id


class DjangoPatchMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    return_field_name = None
    permissions = None
    login_required = None
    auto_context_fields = None
    many_to_many_extras = None
    many_to_one_extras = None
    foreign_key_extras = None
    type_name = None
    field_types = None


class DjangoPatchMutation(DjangoCudBase):
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
            auto_context_fields={},
            many_to_one_extras=None,
            many_to_many_extras=None,
            foreign_key_extras=None,
            type_name=None,
            field_types=None,
            **kwargs,
    ):
        registry = get_global_registry()
        meta_registry = get_type_meta_registry()
        model_type = registry.get_type_for_model(model)

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        if many_to_one_extras is None:
            many_to_one_extras = {}

        if foreign_key_extras is None:
            foreign_key_extras = {}

        if many_to_many_extras is None:
            many_to_many_extras = {}

        input_type_name = type_name or f"Patch{model.__name__}Input"

        model_fields = get_all_optional_input_fields_for_model(
            model,
            only_fields,
            exclude_fields,
            many_to_many_extras=many_to_many_extras,
            foreign_key_extras=foreign_key_extras,
            many_to_one_extras=many_to_one_extras,
            parent_type_name=type_name,
            field_types=field_types,
        )

        InputType = type(input_type_name, (InputObjectType,), model_fields)

        # Register meta-data
        meta_registry.register(
            input_type_name,
            {
                "auto_context_fields": auto_context_fields or {},
                "many_to_many_extras": many_to_many_extras or {},
                "many_to_one_extras": many_to_one_extras or {},
                "foreign_key_extras": foreign_key_extras or {},
                "field_types": field_types or {},
            },
        )

        registry.register_converted_field(input_type_name, InputType)

        arguments = OrderedDict(
            id=graphene.ID(required=True), input=InputType(required=True)
        )

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(model_type)

        _meta = DjangoPatchMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.permissions = permissions
        _meta.auto_context_fields = auto_context_fields or {}
        _meta.InputType = InputType
        _meta.input_type_name = input_type_name
        _meta.many_to_many_extras = many_to_many_extras
        _meta.many_to_one_extras = many_to_one_extras
        _meta.foreign_key_extras = foreign_key_extras
        _meta.field_types = field_types or {}
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def get_queryset(cls, info, **args):
        Model = cls._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, id, input):
        updated_input = cls.before_mutate(root, info, id, input)
        if updated_input:
            input = updated_input

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, id, input)

        id = disambiguate_id(id)
        Model = cls._meta.model
        queryset = cls.get_queryset(info, id=id, input=input)
        obj = queryset.get(pk=id)
        auto_context_fields = cls._meta.auto_context_fields or {}

        cls.validate(root, info, input, id=id, obj=obj)

        with transaction.atomic():
            obj = cls.update_obj(
                obj,
                input,
                info,
                auto_context_fields,
                cls._meta.many_to_many_extras,
                cls._meta.foreign_key_extras,
                cls._meta.many_to_one_extras,
                Model,
            )

            updated_obj = cls.before_save(root, info, obj, id, input)

            if updated_obj:
                obj = updated_obj

            obj.save()

        kwargs = {cls._meta.return_field_name: obj}
        cls.after_mutate(root, info, kwargs)

        return cls(**kwargs)
