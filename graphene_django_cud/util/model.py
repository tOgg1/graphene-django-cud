import binascii
import uuid
from collections import OrderedDict
from typing import Union, List, Optional

import graphene
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from graphene import InputObjectType
from graphene.utils.str_converters import to_camel_case
from graphene_django.registry import get_global_registry
from graphene_django.utils import get_model_fields
from graphql import GraphQLError
from graphql_relay import from_global_id

from graphene_django_cud.converter import (
    convert_django_field_with_choices,
    convert_many_to_many_field,
    is_required,
)
from graphene_django_cud.registry import get_type_meta_registry


def disambiguate_id(ambiguous_id: Union[int, float, str, uuid.UUID]):
    """
    disambiguate_id takes an id which may either be an integer-parsable
    variable, either as a string or a number; or it might be a base64 encoded
    global relay value; or UUID.

    The method then attempts to extract from this token the actual id.

    :return:
    """

    if isinstance(ambiguous_id, (type(None), int, uuid.UUID)):
        return ambiguous_id

    try:
        return int(ambiguous_id)
    except (ValueError, TypeError):
        pass

    if isinstance(ambiguous_id, str):
        try:
            _id = from_global_id(ambiguous_id)[1]

            if _id:
                return _id
        except (ValueError, TypeError, binascii.Error):
            pass

        try:
            return uuid.UUID(ambiguous_id)
        except (ValueError, TypeError, AttributeError):
            pass

        return ambiguous_id

    return None


def disambiguate_ids(ids):
    if not hasattr(ids, "__iter__"):
        return [disambiguate_id(ids)]
    return [disambiguate_id(_id) for _id in ids]


def overload_nested_fields(nested_fields):
    if nested_fields is None:
        return {}
    elif isinstance(nested_fields, dict):
        return nested_fields
    elif hasattr(nested_fields, "__iter__"):
        result = {}
        for el in nested_fields:
            # Should be a string
            if not isinstance(el, str):
                raise ValueError(f"Nested field iterable entry has to be a string. Got {type(el)}")

            result[el] = ["all"]
        return result
    else:
        return {}


def apply_field_name_mappings(model_fields, use_id_suffixes_for_fk, use_id_suffixes_for_m2m, field_name_mappings=None):
    field_name_mappings = field_name_mappings or {}

    if use_id_suffixes_for_fk is None and use_id_suffixes_for_m2m is None and len(field_name_mappings) == 0:
        return {}

    for name, field in model_fields:
        if use_id_suffixes_for_fk and isinstance(field, models.ForeignKey):
            new_name = field_name_mappings.get(name, name + "_id")
            field_name_mappings[name] = new_name
        elif use_id_suffixes_for_m2m and (
                isinstance(field, models.ManyToManyField) or isinstance(field, models.ManyToManyRel)):
            new_name = field_name_mappings.get(name, name + "_ids")
            field_name_mappings[name] = new_name

    return field_name_mappings


def get_input_fields_for_model(
        model,
        fields,
        exclude,
        optional_fields=(),
        required_fields=(),
        many_to_many_extras=None,
        foreign_key_extras=None,
        many_to_one_extras=None,
        one_to_one_extras=None,
        parent_type_name="",
        field_types=None,
        ignore_primary_key=True,
        field_name_mappings=None,
        force_optional_primary_key=False,
) -> OrderedDict:
    registry = get_global_registry()
    meta_registry = get_type_meta_registry()
    field_name_mappings = field_name_mappings or {}

    model_fields = get_model_fields(model)

    many_to_many_extras = resolve_many_to_many_extra_auto_field_names(
        many_to_many_extras or {}, model, parent_type_name
    )
    many_to_one_extras = resolve_many_to_one_extra_auto_field_names(many_to_one_extras or {}, model, parent_type_name)
    foreign_key_extras = resolve_foreign_key_extra_auto_field_names(foreign_key_extras or {}, model, parent_type_name)
    one_to_one_extras = resolve_one_to_one_extra_auto_field_names(one_to_one_extras or {}, model, parent_type_name)

    field_types = field_types or {}
    one_to_one_fields: List[Union[models.OneToOneRel, models.OneToOneField]] = []

    converted_input_fields = OrderedDict()
    fields_lookup = {}

    for name, field in model_fields:
        is_primary_key = getattr(field, "primary_key", False)

        # We ignore the primary key we are told not to.
        if is_primary_key and ignore_primary_key:
            continue

        mapped_name = field_name_mappings.get(name, name)

        # If the field has an override, use that
        if name in field_types:
            converted_input_fields[name] = field_types[name]
            continue

        # Save for later
        fields_lookup[name] = field

        is_not_in_only = fields and name not in fields
        # is_already_created = name in options.fields
        is_excluded = name in exclude  # or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith("+")
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue

        optional_fields = optional_fields or ()
        required_fields = required_fields or ()

        required = None
        if name in optional_fields:
            required = False
        elif name in required_fields:
            required = True

        if is_primary_key and force_optional_primary_key:
            required = False

        converted = convert_django_field_with_choices(
            field,
            registry,
            required,
            many_to_many_extras.get(name, {}).get("exact"),
            foreign_key_extras.get(name, {}),
            one_to_one_extras.get(name, {}),
        )

        # Note: We use the mapped named here, as this is the final input name that will be exposed in the API.
        converted_input_fields[mapped_name] = converted

        if type(field) in (models.OneToOneRel, models.OneToOneField):
            one_to_one_fields.append(field)

    # Create the foreign key extra types here.
    # Note that the dynamic field setup already has been fixed in the first conversion setup.
    for name, data in foreign_key_extras.items():
        field: models.ForeignKey = fields_lookup.get(name)

        if field is None:
            raise ValueError(f"Error adding extras for {name} in model {model}. Field {name} does not exist.")

        type_name = data.get("type")

        if type_name == "ID":
            continue

        # Non auto fields already have their type created
        is_auto_field = data.get("auto")
        if not is_auto_field:
            continue

        # On ForeignKeys we can get the reverse field via field.remote_field
        reverse_field_name = field.remote_field.name

        foreign_key_converted_fields = get_input_fields_for_model(
            field.related_model,
            # TODO: Remove only_fields and exclude_fields when the deprecated fields are removed.
            tuple(data.get("fields", data.get("only_fields", ()))),
            tuple(data.get("exclude", data.get("exclude_fields", ())))
            + (reverse_field_name,),  # Exclude the field referring back to the foreign key
            data.get("optional_fields", ()),
            data.get("required_fields", ()),
            data.get("many_to_many_extras"),
            data.get("foreign_key_extras"),
            data.get("many_to_one_extras"),
            parent_type_name=type_name,
            field_types=data.get("field_types"),
            field_name_mappings=data.get("field_name_mappings"),
        )

        InputType = type(type_name, (InputObjectType,), foreign_key_converted_fields)
        registry.register_converted_field(type_name, InputType)
        meta_registry.register(type_name, data)

    # Create the one to one field types here.
    for name, data in one_to_one_extras.items():
        field: Union[models.OneToOneRel, models.OneToOneField] = fields_lookup.get(name)

        if field is None:
            raise ValueError(f"Error adding extras for {name} in model {model}. Field {name} does not exist.")

        type_name = data.get("type")

        if type_name == "ID":
            continue

        # On OneToOnerels we can get the reverse field name from "field.field.name", as we have a direct
        # reference to the reverse field that way. For OneToOneFields we need to go through "field.target_field".
        reverse_field_name = field.field.name if isinstance(field, models.OneToOneRel) else field.remote_field.name

        one_to_one_converted_fields = get_input_fields_for_model(
            field.related_model,
            # TODO: Remove only_fields and exclude_fields when the deprecated fields are removed.
            tuple(data.get("fields", data.get("only_fields", ()))),
            tuple(data.get("exclude", data.get("exclude_fields", ())))
            + (reverse_field_name,),  # Exclude the field referring back to the foreign key
            data.get("optional_fields", ()),
            data.get("required_fields", ()),
            data.get("many_to_many_extras"),
            data.get("foreign_key_extras"),
            data.get("many_to_one_extras"),
            parent_type_name=type_name,
            field_types=data.get("field_types"),
            field_name_mappings=data.get("field_name_mappings"),
        )

        InputType = type(type_name, (InputObjectType,), one_to_one_converted_fields)
        registry.register_converted_field(type_name, InputType)
        meta_registry.register(type_name, data)

    # Create extra many_to_many_fields
    for name, extras in many_to_many_extras.items():
        field: Optional[Union[models.ManyToManyField, models.ManyToManyRel]] = fields_lookup.get(name)
        if field is None:
            raise GraphQLError(f"Error adding extras for {name} in model {model}. Field {name} does not exist.")

        for extra_name, data in extras.items():

            argument_name = data.get("name", name + "_" + extra_name)

            # Override default
            if extra_name == "exact":
                argument_name = name

            converted_input_fields[argument_name] = convert_many_to_many_like_field(
                data, name, extra_name, parent_type_name, field, registry, meta_registry
            )

    for name, extras in many_to_one_extras.items():
        field: models.ManyToOneRel = fields_lookup.get(name)
        if field is None:
            raise GraphQLError(f"Error adding extras for {name} in model {model}. Field {name} does not exist.")

        for extra_name, data in extras.items():

            argument_name = data.get("name", name + "_" + extra_name)

            # Override default
            if extra_name == "exact":
                argument_name = name

            converted_input_fields[argument_name] = convert_many_to_many_like_field(
                data, name, extra_name, parent_type_name, field, registry, meta_registry
            )

    return converted_input_fields


def convert_many_to_many_like_field(data, name, extra_name, parent_type_name, field, registry, meta_registry):
    if isinstance(data, bool):
        data = {"type": "ID"}

    type_name = data.get("type")

    if type_name and type_name != "ID":
        # Check if type already exists
        existing_type = registry.get_converted_field(type_name)

        if existing_type:
            return graphene.List(existing_type, required=False)

        is_auto_field = data.get("auto", False)
        if not is_auto_field:
            return create_dynamic_list_type(field, type_name, registry, False)

        # Create new type.
        operation_name = data.get("operation", get_likely_operation_from_name(extra_name))

        exclude_fields = ()
        if isinstance(field, models.ManyToOneRel):
            exclude_fields = (field.field.name,)

        converted_fields = get_input_fields_for_model(
            field.related_model,
            data.get("only_fields", ()),
            data.get("exclude_fields", exclude_fields),  # Exclude the field referring back to the foreign key
            data.get("optional_fields", ()),
            data.get("required_fields", ()),
            data.get("many_to_many_extras"),
            data.get("foreign_key_extras"),
            data.get("many_to_one_extras"),
            data.get("one_to_one_extras"),
            parent_type_name=type_name,
            field_types=data.get("field_types"),
            # Don't ignore the primary key on updates
            ignore_primary_key=operation_name != "update" and operation_name != "exact",
            force_optional_primary_key=operation_name == "exact",
        )
        InputType = type(type_name, (InputObjectType,), converted_fields)
        registry.register_converted_field(field, InputType)
        meta_registry.register(
            type_name,
            {
                "auto_context_fields": data.get("auto_context_fields", {}),
                "optional_fields": data.get("optional_fields", ()),
                "required_fields": data.get("required_fields", ()),
                "many_to_many_extras": data.get("many_to_many_extras", {}),
                "many_to_one_extras": data.get("many_to_one_extras", {}),
                "foreign_key_extras": data.get("auto_context_fields", {}),
                "one_to_one_extras": data.get("one_to_one_extras", {}),
                "field_types": data.get("field_types", {}),
            },
        )
        registry.register_converted_field(type_name, InputType)
        _field = graphene.List(
            InputType,
            required=False,
        )
    else:
        _field = convert_many_to_many_field(field, registry, False, data, None)

    return _field


def get_likely_operation_from_name(extra_name):
    extra_name = extra_name.lower()
    if extra_name == "exact":
        return "exact"

    if extra_name == "update" or extra_name == "patch":
        return "update"

    if extra_name == "add" or extra_name == "append" or extra_name == "create":
        return "add"

    if extra_name == "delete" or extra_name == "remove":
        return "remove"

    raise GraphQLError(f"Unknown extra operation {extra_name}")


def _validate_create_many_to_many_extras(extras):
    pass


def _validate_update_many_to_many_extras(extras):
    pass


def validate_many_to_many_extras(extras, operation_type):
    pass


def _validate_create_foreign_key_extras(extras):
    pass


def _validate_update_foreign_key_extras(extras):
    pass


def validate_foreign_key_extras(extras, operation_type):
    pass


def _convert_filter_field(filter_field, model):
    filter_field_split = filter_field.split("__")
    field_name = filter_field_split[0]
    model_field = model._meta.get_field(field_name)

    filter_field_is_list = False
    # In this case, we have a deeply nested field. To find the correct field, we recurse into the string
    if len(filter_field_split) > 2:
        return _convert_filter_field(
            "__".join(filter_field_split[1:]),
            model_field.related_model,  # This fails only on bad input
        )

    if len(filter_field_split) == 2:
        # If we have an "__in" final part of the filter, we are now dealing with
        # a list of things. Note that all other variants can be coerced directly
        # on the filter-call, so we don't really have to deal with other cases here.
        if filter_field_split[1] == "in":
            filter_field_is_list = True
        elif model_field.related_model is not None:
            # Check if the field has a related model. If it does, we recurse one last time, otherwise
            # we are dealing with the final field and some filter, e.g. fieldname__contains.
            return _convert_filter_field(
                "__".join(filter_field_split[1:]),
                model_field.related_model,  # This fails only on bad input
            )

    field_type = convert_django_field_with_choices(model_field, required=False)

    # Handle this case by "deconstructing" the field type class, and pass it as an argument to
    # graphene.List
    if filter_field_is_list:
        field_type = graphene.List(type(field_type), required=False)

    return field_type


def get_filter_fields_input_args(filter_fields, model):
    result = OrderedDict()

    for filter_field in filter_fields:
        result[filter_field] = _convert_filter_field(filter_field, model)

    return result


def is_field_many_to_many(field):
    # We check type equality for ManyToManyRel to ensure we don't get false positives for
    # OnetoOneRel
    return isinstance(field, models.ManyToManyField) or isinstance(field, models.ManyToManyRel)


def is_field_many_to_one(field):
    # ForeignObject.is_multiple is False for e.g. OneToOneRel. We don't handle that here.
    return isinstance(field, models.ManyToOneRel) and field.multiple is True


def is_field_one_to_one(field):
    # We check type equality for OneToOneRel to ensure we don't get false positives for
    # ManyToOneRels
    return isinstance(field, models.OneToOneField) or type(field) == models.OneToOneRel


def get_model_field_or_none(field_name, Model):
    try:
        return Model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None


def get_m2m_all_extras_field_names(extras):
    res = []
    if not extras:
        return []
    for name, extra in extras.items():
        for extra_name, data in extra.items():
            if hasattr(data, "get"):
                argument_name = data.get("name", name + "_" + extra_name)
            else:
                argument_name = name + "_" + extra_name

            if extra_name != "exact":
                res.append(argument_name)
            else:
                res.append(name)

    return res


def get_fk_all_extras_field_names(extras):
    if not extras:
        return []
    return extras.keys()


def resolve_many_to_many_extra_auto_field_names(many_to_many_extras, model, parent_type_name):
    new_many_to_many_extras = {}
    for name, extras in many_to_many_extras.items():
        new_extras = {}
        for extra_name, data in extras.items():
            if isinstance(data, bool):
                data = {}

            type_name = data.get("type", "ID")

            if type_name == "auto":
                operation_name = data.get("operation", get_likely_operation_from_name(extra_name))
                new_extras[extra_name] = {
                    **data,
                    # Add auto marker. This will become important when actually creating the types
                    "auto": True,
                    "type": f"{parent_type_name or ''}"
                            f"{operation_name.capitalize()}{model.__name__}{to_camel_case(name).capitalize()}",
                }
            else:
                new_extras[extra_name] = data

        new_many_to_many_extras[name] = new_extras
    return new_many_to_many_extras


def resolve_many_to_one_extra_auto_field_names(many_to_one_extras, model, parent_type_name):
    new_many_to_one_extras = {}
    for name, extras in many_to_one_extras.items():
        new_extras = {}
        for extra_name, data in extras.items():
            if isinstance(data, bool):
                data = {}

            type_name = data.get("type", "ID")

            if type_name == "auto":
                operation_name = data.get("operation", get_likely_operation_from_name(extra_name))
                new_extras[extra_name] = {
                    **data,
                    "auto": True,
                    "type": f"{parent_type_name or ''}"
                            f"{operation_name.capitalize()}{model.__name__}{to_camel_case(name).capitalize()}",
                }
            else:
                new_extras[extra_name] = data

        new_many_to_one_extras[name] = new_extras
    return new_many_to_one_extras


def resolve_foreign_key_extra_auto_field_names(foreign_key_extras, model, parent_type_name):
    new_foreign_key_extras = {}
    for name, data in foreign_key_extras.items():
        type_name = data.get("type", "ID")

        if type_name == "auto":
            new_foreign_key_extras[name] = {
                **data,
                "auto": True,
                "type": f"{parent_type_name or ''}Create{to_camel_case(name).capitalize()}",
            }
        else:
            new_foreign_key_extras[name] = data
    return new_foreign_key_extras


def resolve_one_to_one_extra_auto_field_names(one_to_one_extras, model, parent_type_name):
    new_one_to_one_extras = {}
    for name, data in one_to_one_extras.items():
        type_name = data.get("type", "ID")

        if type_name == "auto":
            new_one_to_one_extras[name] = {
                **data,
                "type": f"{parent_type_name or ''}Create{to_camel_case(name).capitalize()}",
            }
        else:
            new_one_to_one_extras[name] = data
    return new_one_to_one_extras


def create_dynamic_list_type(field, type_name, registry, required):
    # Use the Input type node from registry in a dynamic type, and create a union with that
    # and the ID
    def dynamic_type():
        _type = registry.get_converted_field(type_name)

        if not _type:
            raise GraphQLError(f"The type {type_name} does not exist.")

        return graphene.List(
            _type,
            description=getattr(field, "help_text", ""),
            required=is_required(field, required, True),
        )

    return graphene.Dynamic(dynamic_type)


def create_dynamic_type(field, type_name, registry, required):
    # Use the Input type node from registry in a dynamic type, and create a union with that
    # and the ID
    def dynamic_type():
        _type = registry.get_converted_field(type_name)

        if not _type:
            raise GraphQLError(f"The type {type_name} does not exist.")

        return _type(
            description=getattr(field, "help_text", ""),
            required=is_required(field, required, True),
        )

    return graphene.Dynamic(dynamic_type)
