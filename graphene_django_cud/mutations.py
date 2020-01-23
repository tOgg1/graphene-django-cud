from collections import OrderedDict
from typing import Iterable

import graphene
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models, transaction
from graphene import Mutation, InputObjectType
from graphene.types.mutation import MutationOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphql import GraphQLError
from graphql_relay import to_global_id

from graphene_django_cud.registry import get_type_meta_registry
from .util import disambiguate_id, disambiguate_ids, get_input_fields_for_model, \
    get_all_optional_input_fields_for_model, is_many_to_many, get_m2m_all_extras_field_names, \
    get_likely_operation_from_name, get_fk_all_extras_field_names, get_filter_fields_input_args

meta_registry = get_type_meta_registry()


class DjangoCudBase(Mutation):
    class Meta:
        abstract = True

    @classmethod
    def get_or_create_foreign_obj(
            cls,
            field,
            value,
            data,
            info
    ):
        field_type = data.get('type', 'ID')

        if field_type == "ID":
            return value
        else:
            input_type_meta = meta_registry.get_meta_for_type(field_type)
            # Create new obj
            related_obj = cls.create_obj(
                value,
                info,
                input_type_meta.get('auto_context_fields', {}),
                input_type_meta.get('many_to_many_extras', {}),
                input_type_meta.get('foreign_key_extras', {}),
                input_type_meta.get('many_to_one_extras', {}),
                field.related_model
            )
            return related_obj.id

    @classmethod
    def get_or_create_m2m_objs(
            cls,
            field,
            values,
            data,
            operation,
            info
    ):
        results = []

        if not values:
            return results

        if isinstance(data, bool):
            data = {}

        field_type = data.get('type', 'ID')

        for value in values:
            if field_type == "ID":
                related_obj = field.related_model.objects.get(pk=disambiguate_id(value))
            else:
                # This is something that we are going to create
                input_type_meta = meta_registry.get_meta_for_type(field_type)
                # Create new obj
                related_obj = cls.create_obj(
                    value,
                    info,
                    input_type_meta.get('auto_context_fields', {}),
                    input_type_meta.get('many_to_many_extras', {}),
                    input_type_meta.get('foreign_key_extras', {}),
                    input_type_meta.get('many_to_one_extras', {}),
                    field.related_model
                )
            results.append(related_obj)

        return results

    @classmethod
    def get_or_create_m2o_objs(
            cls,
            obj,
            field,
            values,
            data,
            operation,
            info,
            Model
    ):
        results = []

        if not values:
            return results

        field_type = data.get('type', 'auto')
        for value in values:
            if field_type == "ID":
                related_obj = field.related_model.objects.get(pk=disambiguate_id(value))
                results.append(related_obj)
            elif field_type == "auto":
                # In this case, a new type has been created for us. Let's first find it's name,
                # then get it's meta, and then create it. We also need to attach the obj as the
                # foreign key.
                _type_name = data.get('type_name', f"Create{Model.__name__}{field.name.capitalize()}")
                input_type_meta = meta_registry.get_meta_for_type(field_type)

                # .id has to be called here, as the regular input for a foreignkey is ID!
                value[field.field.name] = obj.id
                related_obj = cls.create_obj(
                    value,
                    info,
                    input_type_meta.get('auto_context_fields', {}),
                    input_type_meta.get('many_to_many_extras', {}),
                    input_type_meta.get('foreign_key_extras', {}),
                    input_type_meta.get('many_to_one_extras', {}),
                    field.related_model
                )
                results.append(related_obj)
            else:
                # This is something that we are going to create
                input_type_meta = meta_registry.get_meta_for_type(field_type)
                # Create new obj
                related_obj = cls.create_obj(
                    value,
                    info,
                    input_type_meta.get('auto_context_fields', {}),
                    input_type_meta.get('many_to_many_extras', {}),
                    input_type_meta.get('foreign_key_extras', {}),
                    input_type_meta.get('many_to_one_extras', {}),
                    field.related_model
                )
                results.append(related_obj)

        return results

    @classmethod
    def create_obj(
            cls,
            input,
            info,
            auto_context_fields,
            many_to_many_extras,
            foreign_key_extras,
            many_to_one_extras,
            Model
    ):
        meta_registry = get_type_meta_registry()

        model_field_values = {}
        many_to_many_values = {}

        many_to_many_extras_field_names = get_m2m_all_extras_field_names(many_to_many_extras)
        many_to_one_extras_field_names = get_m2m_all_extras_field_names(many_to_one_extras)  # The layout is the same as for m2m
        foreign_key_extras_field_names = get_fk_all_extras_field_names(foreign_key_extras)

        for field_name, context_name in auto_context_fields.items():
            if hasattr(info.context, context_name):
                model_field_values[field_name] = getattr(info.context, context_name)

        for name, value in super(type(input), input).items():
            # Handle these separately
            if name in many_to_many_extras_field_names or name in foreign_key_extras_field_names or name in many_to_one_extras_field_names:
                continue

            field = Model._meta.get_field(name)
            new_value = value

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_many = is_many_to_many(field)

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
                elif field_is_many_to_many:
                    new_value = disambiguate_ids(value)


            if field_is_many_to_many:
                many_to_many_values[name] = new_value
            else:
                model_field_values[name] = new_value

        # We don't have an object yet, and we potentially need to create
        # parents before proceeding.
        for name, extras in foreign_key_extras.items():
            value = input.get(name, None)
            field = Model._meta.get_field(name)

            obj_id = cls.get_or_create_foreign_obj(
                field,
                value,
                extras,
                info
            )

            model_field_values[name + "_id"] = obj_id

        # Foreign keys are added, we are ready to create our object
        obj = Model.objects.create(**model_field_values)

        for name, values in many_to_many_values.items():
            getattr(obj, name).set(values)

        # Handle extras fields
        many_to_many_to_add = {}
        many_to_many_to_remove = {}
        many_to_many_to_set = {}
        for name, extras in many_to_many_extras.items():
            field = Model._meta.get_field(name)
            if not name in many_to_many_to_add:
                many_to_many_to_add[name] = []
                many_to_many_to_remove[name] = []
                many_to_many_to_set[name] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if isinstance(data, bool):
                    data = {}

                operation = data.get('operation') or get_likely_operation_from_name(extra_name)
                objs = cls.get_or_create_m2m_objs(
                    field,
                    values,
                    data,
                    operation,
                    info
                )

                if operation == "exact":
                    many_to_many_to_set[name] = objs
                elif len(objs) > 0:
                    if operation == "add":
                        many_to_many_to_add[name] += objs
                    else:
                        many_to_many_to_remove[name] += objs


        many_to_one_to_add = {}
        many_to_one_to_remove = {}
        many_to_one_to_set = {}
        for name, extras in many_to_one_extras.items():
            field = Model._meta.get_field(name)

            if not name in many_to_one_to_add:
                many_to_one_to_add[name] = []
                many_to_one_to_remove[name] = []
                many_to_one_to_set[name] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if values is None:
                    continue

                if isinstance(data, bool):
                    data = {}

                operation = data.get('operation') or get_likely_operation_from_name(extra_name)

                if operation == "exact":
                    objs = cls.get_or_create_m2o_objs(
                        obj,
                        field,
                        values,
                        data,
                        operation,
                        info,
                        Model
                    )
                    many_to_one_to_set[name] = objs
                elif operation == "add":
                    objs = cls.get_or_create_m2o_objs(
                        obj,
                        field,
                        values,
                        data,
                        operation,
                        info,
                        Model
                    )
                    many_to_one_to_add[name] += objs
                else:
                    many_to_one_to_remove[name] += disambiguate_ids(values)

        for name, objs in many_to_one_to_set.items():
            if objs is not None:
                field = getattr(obj, name)
                if hasattr(field, 'remove'):
                    # In this case, the relationship is nullable, and we can clear it, and then add the relevant objects
                    field.clear()
                    field.add(*objs)
                else:
                    # Remove the related objects by deletion, and set the new ones.
                    field.exclude(id__in=[obj.id for obj in objs]).delete()
                    getattr(obj, name).add(*objs)

        for name, objs in many_to_one_to_add.items():
            getattr(obj, name).add(*objs)

        for name, objs in many_to_one_to_remove.items():
            field = getattr(obj, name)
            if hasattr(field, 'remove'):
                # The field is nullable, and we simply remove the relation
                related_name = Model._meta.get_field(name).remote_field.name
                getattr(obj, name).filter(id__in=objs).update(**{
                    related_name: None
                })
            else:
                # Only nullable foreign key reverse rels have the remove method.
                # For other's we have to delete the relations
                getattr(obj, name).filter(id__in=objs).delete()

        for name, objs in many_to_many_to_set.items():
            if objs is not None:
                getattr(obj, name).set(objs)

        for name, objs in many_to_many_to_add.items():
            getattr(obj, name).add(*objs)

        for name, objs in many_to_many_to_remove.items():
            getattr(obj, name).remove(*objs)

        return obj


    @classmethod
    def update_obj(
            cls,
            obj,
            input,
            info,
            auto_context_fields,
            many_to_many_extras,
            foreign_key_extras,
            many_to_one_extras,
            Model
    ):

        many_to_many_values = {}
        many_to_many_add_values = {}
        many_to_many_remove_values = {}

        many_to_many_extras_field_names = get_m2m_all_extras_field_names(many_to_many_extras)
        many_to_one_extras_field_names = get_m2m_all_extras_field_names(many_to_one_extras)  # The layout is the same as for m2m
        foreign_key_extras_field_names = get_fk_all_extras_field_names(foreign_key_extras)

        for field_name, context_name in auto_context_fields.items():
            if hasattr(info.context, context_name):
                setattr(obj, field_name, getattr(info.context, context_name))

        for name, value in super(type(input), input).items():
            # Handle these separately
            if name in many_to_many_extras_field_names or name in foreign_key_extras_field_names or name in many_to_one_extras_field_names:
                continue

            field = Model._meta.get_field(name)
            new_value = value

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_many = is_many_to_many(field)

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
                elif field_is_many_to_many:
                    new_value = disambiguate_ids(value)

            if field_is_many_to_many:
                many_to_many_values[name] = new_value
            else:
                setattr(obj, name, new_value)

        # Handle extras fields
        for name, extras in foreign_key_extras.items():
            value = input.get(name, None)
            field = Model._meta.get_field(name)

            obj_id = cls.get_or_create_foreign_obj(
                field,
                value,
                extras,
                info
            )
            setattr(obj, name + "_id", obj_id)

        many_to_many_to_add = {}
        many_to_many_to_remove = {}
        many_to_many_to_set = {}
        for name, extras in many_to_many_extras.items():
            field = Model._meta.get_field(name)
            if not name in many_to_many_to_add:
                many_to_many_to_add[name] = []
                many_to_many_to_remove[name] = []
                many_to_many_to_set[name] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if isinstance(data, bool):
                    data = {}

                operation = data.get('operation') or get_likely_operation_from_name(extra_name)
                objs = cls.get_or_create_m2m_objs(
                    field,
                    values,
                    data,
                    operation,
                    info
                )

                if operation == "exact":
                    many_to_many_to_set[name] = objs
                elif operation == "add":
                    many_to_many_to_add[name] += objs
                else:
                    many_to_many_to_remove[name] += objs

        many_to_one_to_add = {}
        many_to_one_to_remove = {}
        many_to_one_to_set = {}
        for name, extras in many_to_one_extras.items():
            field = Model._meta.get_field(name)

            if not name in many_to_one_to_add:
                many_to_one_to_add[name] = []
                many_to_one_to_remove[name] = []
                many_to_one_to_set[name] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if values is None:
                    continue

                if isinstance(data, bool):
                    data = {}

                operation = data.get('operation') or get_likely_operation_from_name(extra_name)

                if operation == "exact":
                    objs = cls.get_or_create_m2o_objs(
                        obj,
                        field,
                        values,
                        data,
                        operation,
                        info,
                        Model
                    )
                    many_to_one_to_set[name] = objs
                elif operation == "add":
                    objs = cls.get_or_create_m2o_objs(
                        obj,
                        field,
                        values,
                        data,
                        operation,
                        info,
                        Model
                    )
                    many_to_one_to_add[name] += objs
                else:
                    many_to_one_to_remove[name] += disambiguate_ids(values)

        for name, objs in many_to_one_to_set.items():
            if objs is not None:
                field = getattr(obj, name)
                if hasattr(field, 'remove'):
                    # In this case, the relationship is nullable, and we can clear it, and then add the relevant objects
                    field.clear()
                    field.add(*objs)
                else:
                    # Remove the related objects by deletion, and set the new ones.
                    field.exclude(id__in=[obj.id for obj in objs]).delete()
                    getattr(obj, name).add(*objs)

        for name, objs in many_to_one_to_add.items():
            getattr(obj, name).add(*objs)

        for name, objs in many_to_one_to_remove.items():
            field = getattr(obj, name)
            if hasattr(field, 'remove'):
                # The field is nullable, and we simply remove the relation
                related_name = Model._meta.get_field(name).remote_field.name
                getattr(obj, name).filter(id__in=objs).update(**{
                    related_name: None
                })
            else:
                # Only nullable foreign key reverse rels have the remove method.
                # For other's we have to delete the relations
                getattr(obj, name).filter(id__in=objs).delete()

        for name, objs in many_to_many_to_set.items():
            if objs is not None:
                getattr(obj, name).set(objs)

        for name, objs in many_to_many_to_add.items():
            getattr(obj, name).add(*objs)

        for name, objs in many_to_many_to_remove.items():
            getattr(obj, name).remove(*objs)

        return obj

    @classmethod
    def get_permissions(cls, root, info, *args, **kwargs) -> Iterable[str]:
        return cls._meta.permissions

    @classmethod
    def check_permissions(cls, root, info, *args, **kwargs) -> None:
        get_permissions = getattr(cls, 'get_permissions', None)
        if not callable(get_permissions):
            raise TypeError("The `get_permissions` attribute of a mutation must be callable.")

        permissions = cls.get_permissions(root, info, *args, **kwargs)

        if permissions and len(permissions) > 0:
            if not info.context.user.has_perms(permissions):
                raise GraphQLError("Not permitted to access this mutation.")

    @classmethod
    def validate(cls, root, info, input, **kwargs):
        for name, value in super(type(input), input).items():
            validate_field_name = f"validate_{name}"
            validate_field = getattr(cls, validate_field_name, None)

            if validate_field and callable(validate_field):
                validate_field(root, info, value, input, **kwargs)

    @classmethod
    def before_mutate(cls, root, info, *args, **kwargs):
        return None

    @classmethod
    def before_save(cls, root, info, *args, **kwargs):
        return None

    @classmethod
    def after_mutate(cls, root, info, *args, **kwargs):
        return None


class DjangoUpdateMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    permissions = None
    login_required = None
    auto_context_fields = None
    optional_fields = ()
    required_fields = None
    type_name = None
    return_field_name = None
    many_to_many_extras = None
    many_to_one_extras=None
    foreign_key_extras = None
    field_types = None


class DjangoUpdateMutation(DjangoCudBase):
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
            many_to_many_extras=None,
            many_to_one_extras=None,
            foreign_key_extras=None,
            type_name="",
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

        input_type_name = type_name or f"Update{model.__name__}Input"

        model_fields = get_input_fields_for_model(
            model,
            only_fields,
            exclude_fields,
            optional_fields=tuple(auto_context_fields.keys()) + optional_fields,
            required_fields=required_fields,
            many_to_many_extras=many_to_many_extras,
            foreign_key_extras=foreign_key_extras,
            many_to_one_extras=many_to_one_extras,
            parent_type_name=input_type_name,
            field_types=field_types,
        )

        InputType = type(
            input_type_name, (InputObjectType,), model_fields
        )

        # Register meta-data
        meta_registry.register(
            input_type_name,
            {
                'auto_context_fields': auto_context_fields or {},
                'optional_fields': optional_fields,
                'required_fields': required_fields,
                'many_to_many_extras': many_to_many_extras or {},
                'many_to_one_extras': many_to_one_extras or {},
                'foreign_key_extras': foreign_key_extras or {},
                'field_types': field_types or {},
            }
        )

        registry.register_converted_field(
            input_type_name,
            InputType
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
        updated_input = cls.before_mutate(
            root,
            info,
            id,
            input
        )
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
                Model
            )

            updated_obj = cls.before_save(
                root,
                info,
                obj,
                id,
                input
            )

            if updated_obj:
                obj = updated_obj

            obj.save()

        kwargs = {cls._meta.return_field_name: obj}
        cls.after_mutate(root, info, kwargs)

        return cls(**kwargs)


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
            many_to_one_extras = None,
            many_to_many_extras = None,
            foreign_key_extras = None,
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
            field_types=field_types
        )

        InputType = type(
            input_type_name, (InputObjectType,), model_fields
        )

        # Register meta-data
        meta_registry.register(
            input_type_name,
            {
                'auto_context_fields': auto_context_fields or {},
                'many_to_many_extras': many_to_many_extras or {},
                'many_to_one_extras': many_to_one_extras or {},
                'foreign_key_extras': foreign_key_extras or {},
                'field_types': field_types or {},
            }
        )

        registry.register_converted_field(
            input_type_name,
            InputType
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
        updated_input = cls.before_mutate(
            root,
            info,
            id,
            input
        )
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
                Model
            )

            updated_obj = cls.before_save(
                root,
                info,
                obj,
                id,
                input
            )

            if updated_obj:
                obj = updated_obj

            obj.save()

        kwargs = {cls._meta.return_field_name: obj}
        cls.after_mutate(root, info, kwargs)

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
    many_to_many_extras = None
    many_to_one_extras = None
    foreign_key_extras = None
    type_name = None
    field_types=None


class DjangoCreateMutation(DjangoCudBase):
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
            many_to_many_extras=None,
            foreign_key_extras = None,
            many_to_one_extras = None,
            type_name=None,
            field_types=None,
            **kwargs,
    ):
        registry = get_global_registry()
        meta_registry = get_type_meta_registry()
        model_type = registry.get_type_for_model(model)

        if many_to_one_extras is None:
            many_to_one_extras = {}

        if foreign_key_extras is None:
            foreign_key_extras = {}

        if many_to_many_extras is None:
            many_to_many_extras = {}

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        input_type_name = type_name or f"Create{model.__name__}Input"

        model_fields = get_input_fields_for_model(
            model,
            only_fields,
            exclude_fields,
            tuple(auto_context_fields.keys()) + optional_fields,
            required_fields,
            many_to_many_extras,
            foreign_key_extras,
            many_to_one_extras,
            parent_type_name=input_type_name,
            field_types=field_types,
        )

        InputType = type(
            input_type_name, (InputObjectType,), model_fields
        )

        # Register meta-data
        meta_registry.register(
            input_type_name,
            {
                'auto_context_fields': auto_context_fields or {},
                'optional_fields': optional_fields,
                'required_fields': required_fields,
                'many_to_many_extras': many_to_many_extras or {},
                'foreign_key_extras': foreign_key_extras or {},
                'field_types': field_types or {}
            }
        )

        registry.register_converted_field(
            input_type_name,
            InputType
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
        _meta.many_to_many_extras = many_to_many_extras or {}
        _meta.foreign_key_extras = foreign_key_extras
        _meta.many_to_one_extras = many_to_one_extras or {}
        _meta.field_types = field_types or {}
        _meta.InputType = InputType
        _meta.input_type_name = input_type_name
        _meta.login_required = _meta.login_required or (
            _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)


    @classmethod
    def mutate(cls, root, info, input):
        updated_input = cls.before_mutate(
            root,
            info,
            input
        )
        if updated_input:
            input = updated_input

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, input)
        cls.validate(root, info, input)

        Model = cls._meta.model
        model_field_values = {}
        auto_context_fields = cls._meta.auto_context_fields or {}

        with transaction.atomic():
            obj = cls.create_obj(
                input,
                info,
                auto_context_fields,
                cls._meta.many_to_many_extras,
                cls._meta.foreign_key_extras,
                cls._meta.many_to_one_extras,
                Model
            )
            updated_obj = cls.before_save(
                root,
                info,
                input
            )
            if updated_obj:
                updated_obj.save()



        kwargs = {cls._meta.return_field_name: obj}
        cls.after_mutate(root, info, kwargs)

        return cls(**kwargs)


class DjangoBatchCreateMutationOptions(MutationOptions):
    model = None
    only_fields = None
    exclude_fields = None
    return_field_name = None
    permissions = None
    login_required = None
    auto_context_fields = None
    optional_fields = ()
    required_fields = ()
    many_to_many_extras = None
    many_to_one_extras = None
    foreign_key_extras = None
    type_name = None
    use_type_name = None
    field_types = None


class DjangoBatchCreateMutation(DjangoCudBase):
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
            many_to_many_extras=None,
            foreign_key_extras = None,
            many_to_one_extras = None,
            type_name=None,
            use_type_name=None,
            field_types=None,
            **kwargs,
    ):
        registry = get_global_registry()
        meta_registry = get_type_meta_registry()
        model_type = registry.get_type_for_model(model)

        if many_to_one_extras is None:
            many_to_one_extras = {}

        if foreign_key_extras is None:
            foreign_key_extras = {}

        if many_to_many_extras is None:
            many_to_many_extras = {}

        assert model_type, f"Model type must be registered for model {model}"

        if not return_field_name:
            # Pluralize
            return_field_name = to_snake_case(model.__name__) + "s"

        if use_type_name:
            input_type_name = use_type_name
            InputType = registry.get_converted_field(
                input_type_name
            )
            if not InputType:
                raise GraphQLError(f"Could not find input type with name {input_type_name}")
        else:
            input_type_name = type_name or f"BatchCreate{model.__name__}Input"

            model_fields = get_input_fields_for_model(
                model,
                only_fields,
                exclude_fields,
                tuple(auto_context_fields.keys()) + optional_fields,
                required_fields,
                many_to_many_extras,
                foreign_key_extras,
                many_to_one_extras,
                parent_type_name=input_type_name,
                field_types=field_types,
            )

            InputType = type(
                input_type_name, (InputObjectType,), model_fields
            )

            # Register meta-data
            meta_registry.register(
                input_type_name,
                {
                    'auto_context_fields': auto_context_fields or {},
                    'optional_fields': optional_fields,
                    'required_fields': required_fields,
                    'many_to_many_extras': many_to_many_extras or {},
                    'foreign_key_extras': foreign_key_extras or {},
                    'field_types': field_types or {}
                }
            )

            registry.register_converted_field(
                input_type_name,
                InputType
            )

        arguments = OrderedDict(input=graphene.List(InputType, required=True))

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.List(model_type)

        _meta = DjangoBatchCreateMutationOptions(cls)
        _meta.model = model
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.return_field_name = return_field_name
        _meta.optional_fields = optional_fields
        _meta.required_fields = required_fields
        _meta.permissions = permissions
        _meta.auto_context_fields = auto_context_fields or {}
        _meta.many_to_many_extras = many_to_many_extras or {}
        _meta.foreign_key_extras = foreign_key_extras
        _meta.many_to_one_extras = many_to_one_extras or {}
        _meta.field_types = field_types or {}
        _meta.InputType = InputType
        _meta.input_type_name = input_type_name
        _meta.login_required = _meta.login_required or (
                _meta.permissions and len(_meta.permissions) > 0
        )

        super().__init_subclass_with_meta__(arguments=arguments, _meta=_meta, **kwargs)

    @classmethod
    def mutate(cls, root, info, input):
        updated_input = cls.before_mutate(
            root,
            info,
            input
        )
        if updated_input:
            input = updated_input

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, input)

        Model = cls._meta.model
        model_field_values = {}
        auto_context_fields = cls._meta.auto_context_fields or {}

        created_objs = []

        with transaction.atomic():
            for data in input:
                cls.validate(root, info, data, full_input=input)
                obj = cls.create_obj(
                    data,
                    info,
                    auto_context_fields,
                    cls._meta.many_to_many_extras,
                    cls._meta.foreign_key_extras,
                    cls._meta.many_to_one_extras,
                    Model
                )
                created_objs.append(obj)

            updated_objs = cls.before_save(
                root,
                info,
                created_objs
            )
            if updated_objs:
                created_objs = updated_objs

        kwargs = {cls._meta.return_field_name: created_objs}
        cls.after_mutate(root, info, kwargs)
        return cls(**kwargs)


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
    def get_queryset(cls, info, **args):
        Model = cls._meta.model
        return Model.objects

    @classmethod
    def mutate(cls, root, info, id):
        cls.before_mutate(
            root,
            info,
            id
        )

        if cls._meta.login_required and not info.context.user.is_authenticated:
            raise GraphQLError("Must be logged in to access this mutation.")

        cls.check_permissions(root, info, id)

        Model = cls._meta.model
        id = disambiguate_id(id)

        try:
            obj = cls.get_queryset(info, id=id).get(pk=id)
            cls.before_save(
                root,
                info,
                obj,
                id
            )
            obj.delete()
            cls.after_mutate(
                root,
                info,

            )
            return cls(found=True, deleted_id=id)
        except ObjectDoesNotExist:
            return cls(found=False)


class DjangoBatchDeleteMutationOptions(MutationOptions):
    model = None
    filter_fields = None
    filter_class = None
    permissions = None
    login_required = None


class DjangoBatchDeleteMutation(DjangoCudBase):
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

        input_arguments = get_filter_fields_input_args(
            filter_fields,
            model
        )

        InputType = type(
            f"BatchDelete{model.__name__}Input", (InputObjectType,), input_arguments
        )

        arguments = OrderedDict(input=InputType(required=True))

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
    def get_queryset(cls, info, **args):
        Model = cls._meta.model
        return Model.objects


    @classmethod
    def mutate(cls, root, info, input):
        updated_input = cls.before_mutate(
            root,
            info,
            input
        )

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
                    new_value = disambiguate_id(value)
                elif type(field) in (
                        models.ManyToManyField,
                        models.ManyToManyRel,
                        models.ManyToOneRel,
                ) or filter_field_is_list:
                    new_value = disambiguate_ids(value)

            model_field_values[name] = new_value

        filter_qs = cls.get_queryset(info, input=input).filter(**model_field_values)
        updated_qs = cls.before_save(
            root,
            info,
            filter_qs
        )

        if updated_qs:
            filter_qs = updated_qs

        ids = [
            to_global_id(get_global_registry().get_type_for_model(Model).__name__, id)
            for id in filter_qs.values_list("id", flat=True)
        ]

        deletion_count, _ = filter_qs.delete()

        cls.after_mutate(
            root,
            info,
            deletion_count,
            ids
        )

        return cls(deletion_count=deletion_count, deleted_ids=ids)
