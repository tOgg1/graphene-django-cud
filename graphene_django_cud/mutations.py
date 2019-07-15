import datetime
import re
from collections import OrderedDict

import graphene
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from graphene import Mutation, InputObjectType
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError
from graphql.language import ast
from graphql_relay import to_global_id

from .util import disambiguate_id, disambiguate_ids, get_input_fields_for_model, get_all_optional_input_fields_for_model


class DjangoUpdateMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    return_field_name = None
    permissions = None
    login_required = None
    auto_context_fields = None
    optional_fields = ()
    required_fields = ()


class DjangoUpdateMutation(Mutation):
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
            auto_context_fields={},
            optional_fields=(),
            required_fields=(),
            return_field_name=None,
            **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        model_fields = get_input_fields_for_model(
            model, registry, only_fields, exclude_fields, tuple(auto_context_fields.keys()) + optional_fields, required_fields
        )

        InputType = type(
            f"Update{model.__name__}Input", (InputObjectType,), model_fields
        )

        arguments = OrderedDict(
            id=graphene.ID(required=True), input=InputType(required=True)
        )

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(model_type)

        _meta = DjangoUpdateMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.permissions = permissions
        _meta.auto_context_fields = auto_context_fields or {}
        _meta.optional_fields = optional_fields
        _meta.required_fields = required_fields
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    def get_queryset(self):
        Model = self._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, id, input):
        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        if cls._meta.permissions and len(cls._meta.permissions) > 0:
            if not info.context.user.has_perms(cls._meta.permissions):
                raise GraphQLError("Not permitted to access this mutation.")

        id = disambiguate_id(id)
        Model = cls._meta.model
        queryset = cls.get_queryset(Model)
        obj = queryset.get(pk=id)
        auto_context_fields = cls._meta.auto_context_fields or {}

        for field_name, context_name in cls._meta.auto_context_fields.items():
            if hasattr(info.context, context_name):
                setattr(obj, field_name, getattr(info.context, context_name))

        for name, value in input.items():
            field = Model._meta.get_field(name)

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
                    # Delete auto context field here, if it exists. We have to do this explicitly
                    # as we change the name below
                    if name in auto_context_fields:
                        setattr(obj, name, None)

                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = disambiguate_id(value)
                elif type(field) in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                ):
                    new_value = disambiguate_ids(value)

            setattr(obj, name, new_value)

        obj.save()
        kwargs = {cls._meta.return_field_name: obj}

        return cls(**kwargs)


class DjangoPatchMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    return_field_name = None
    permissions = None
    login_required = None
    auto_context_fields = None


class DjangoPatchMutation(Mutation):
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
            **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        model_fields = get_all_optional_input_fields_for_model(
            model, registry, only_fields, exclude_fields
        )

        InputType = type(
            f"Patch{model.__name__}Input", (InputObjectType,), model_fields
        )

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
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    def get_queryset(self):
        Model = self._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, id, input):
        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        if cls._meta.permissions and len(cls._meta.permissions) > 0:
            if not info.context.user.has_perms(cls._meta.permissions):
                raise GraphQLError("Not permitted to access this mutation.")

        id = disambiguate_id(id)
        Model = cls._meta.model
        queryset = cls.get_queryset(Model)
        obj = queryset.get(pk=id)
        auto_context_fields = cls._meta.auto_context_fields or {}

        for field_name, context_name in cls._meta.auto_context_fields.items():
            if hasattr(info.context, context_name):
                setattr(obj, field_name, getattr(info.context, context_name))

        for name, value in input.items():
            field = Model._meta.get_field(name)

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
                    # Delete auto context field here, if it exists. We have to do this explicitly
                    # as we change the name below
                    if name in auto_context_fields:
                        setattr(obj, name, None)

                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = disambiguate_id(value)
                elif type(field) in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                ):
                    new_value = disambiguate_ids(value)

            setattr(obj, name, new_value)

        obj.save()
        kwargs = {cls._meta.return_field_name: obj}

        return cls(**kwargs)


class DjangoCreateMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    return_field_name = None
    permissions = None
    login_required = None
    auto_context_fields = None
    optional_fields = ()
    required_fields = ()


class DjangoCreateMutation(Mutation):
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
            optional_fields=(),
            required_fields=(),
            auto_context_fields={},
            return_field_name=None,
            **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        model_fields = get_input_fields_for_model(
            model, registry, only_fields, exclude_fields, tuple(auto_context_fields.keys()) + optional_fields, required_fields
        )

        InputType = type(
            f"Create{model.__name__}Input", (InputObjectType,), model_fields
        )

        arguments = OrderedDict(input=InputType(required=True))

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(model_type)

        _meta = DjangoCreateMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.optional_fields = optional_fields
        _meta.required_fields = required_fields
        _meta.permissions = permissions
        _meta.auto_context_fields = auto_context_fields or {}
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def mutate(cls, root, info, input):
        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        if cls._meta.permissions and len(cls._meta.permissions) > 0:
            if not info.context.user.has_perms(cls._meta.permissions):
                raise GraphQLError("Not permitted to access this mutation.")

        Model = cls._meta.model
        model_field_values = {}
        auto_context_fields = cls._meta.auto_context_fields or {}

        for field_name, context_name in cls._meta.auto_context_fields.items():
            if hasattr(info.context, context_name):
                model_field_values[field_name] = getattr(info.context, context_name)

        for name, value in input.items():
            field = Model._meta.get_field(name)

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
                    # Delete auto context field here, if it exists. We have to do this explicitly
                    # as we change the name below
                    if name in auto_context_fields:
                        del model_field_values[name]

                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = disambiguate_id(value)
                elif type(field) in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                ):
                    new_value = disambiguate_ids(value)

            model_field_values[name] = new_value

        obj = Model.objects.create(**model_field_values)

        kwargs = {cls._meta.return_field_name: obj}

        return cls(**kwargs)


class DjangoDeleteMutationOptions(MutationOptions):
    model = None
    permissions = None
    login_required = None


class DjangoDeleteMutation(Mutation):
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
    def mutate(cls, root, info, id):
        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        if cls._meta.permissions and len(cls._meta.permissions) > 0:
            if not info.context.user.has_perms(cls._meta.permissions):
                raise GraphQLError("Not permitted to access this mutation.")

        Model = cls._meta.model

        try:
            obj = Model.objects.get(pk=id)
            obj.delete()
            return cls(found=True, deleted_id=id)
        except ObjectDoesNotExist:
            return cls(found=False)


class DjangoBatchDeleteMutationOptions(MutationOptions):
    model = None
    filter_fields = None
    filter_class = None
    permissions = None
    login_required = None


class DjangoBatchDeleteMutation(Mutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
            cls,
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

        input_arguments = OrderedDict()
        for field in filter_fields:
            input_arguments[field] = graphene.String()

        InputType = type(
            f"BatchDelete{model.__name__}Input", (InputObjectType,), input_arguments
        )

        arguments = OrderedDict(filter=InputType(required=True))

        output_fields = OrderedDict()
        output_fields["deletion_count"] = graphene.Int()
        output_fields["deleted_ids"] = graphene.List(graphene.ID)

        _meta = DjangoBatchDeleteMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.filter_fields = filter_fields
        _meta.permissions = permissions
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def mutate(cls, root, info, filter):
        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        if cls._meta.permissions and len(cls._meta.permissions) > 0:
            if not info.context.user.has_perms(cls._meta.permissions):
                raise GraphQLError("Not permitted to access this mutation.")

        Model = cls._meta.model
        model_field_values = {}

        for name, value in filter.items():
            try:
                field = Model._meta.get_field(name)
            except FieldDoesNotExist:
                # This can happen with nested selectors. In this case we set the field to none.
                field = None

            new_value = value

            value_handle_name = "handle_" + name
            if hasattr(cls, value_handle_name):
                handle_func = getattr(cls, value_handle_name)
                assert callable(
                    handle_func
                ), f"Property {value_handle_name} on {cls.__name__} is not a function."
                new_value = handle_func(value, name, info)

            # On some fields we perform some default conversion, if the value was not transformed above.
            if new_value == value and field is not None and value is not None:
                if type(field) in (models.ForeignKey, models.OneToOneField):
                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = disambiguate_id(value)
                elif type(field) in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                ):
                    new_value = disambiguate_ids(value)

            model_field_values[name] = new_value

        filter_qs = Model.objects.filter(**model_field_values)
        ids = [
            to_global_id(get_global_registry().get_type_for_model(Model).__name__, id)
            for id in filter_qs.values_list("id", flat=True)
        ]
        deletion_count, _ = filter_qs.delete()

        return cls(deletion_count=deletion_count, deleted_ids=ids)


class TimeDelta(graphene.Scalar):
    """
    TimeDelta is a graphene scalar for rendering and parsing datetime.timedelta objects.
    """

    regex = re.compile(r"(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+?)?")

    @staticmethod
    def serialize(timedelta: datetime.timedelta):
        hours = timedelta.seconds // 3600
        if timedelta.days > 0:
            hours = timedelta.days * 24
        minutes = (timedelta.seconds // 60) % 60
        seconds = timedelta.seconds % 60

        return_string = f"{str(hours).zfill(2)}:{str(minutes).zfill(2)}"

        if seconds:
            return_string += f":{str(seconds).zfill(2)}"

        return return_string

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return TimeDelta.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        match = TimeDelta.regex.match(value)

        if not match:
            raise GraphQLError(f"Error parsing TimeDelta node with format {value}.")

        days = 0
        hours = int(match.group("hours"))
        minutes = int(match.group("minutes"))
        seconds = match.group("seconds")

        if hours > 23:
            days = hours // 24
            hours = hours % 24

        if seconds:
            seconds = int(seconds)

        return timezone.timedelta(
            days=days, hours=hours, minutes=minutes, seconds=seconds
        )

