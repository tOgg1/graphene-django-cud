# This file is more or less a copy of graphene_django/converter.py, with a few exceptions:
#   * All fields here are considered input fields, and hence all foreign relationships will be converted
#     to either graphene.ID() or lists thereof.
#   * `required` can be specified in the conversion method.
#   * fields with a `default` value are never required unless explicitly set so.
#   * DateTime and Date fields with `auto_now` or `auto_now_add` are converted to None unless
#     they are explicitly required or not required.
#
# From the last point, users of this module are expected to discard any field returning None
from functools import singledispatch

from django.db import models
from django.db.models import FileField, ImageField
from django.utils.encoding import force_str
from graphene import (
    ID,
    Boolean,
    Enum,
    Float,
    Int,
    List,
    NonNull,
    String,
    UUID,
    DateTime,
    Date,
    Time,
    InputField,
    Dynamic,
    Decimal,
)
from graphene.types.json import JSONString
from graphene.utils.str_converters import to_camel_case, to_const
from graphene_django.compat import ArrayField, HStoreField, JSONField, RangeField
from graphene_file_upload.scalars import Upload
from graphql import assert_valid_name, GraphQLError

from graphene_django_cud.types import TimeDelta


def is_required(field, required=None, is_many_to_many=False):
    if required is not None:
        return required

    field_default = getattr(field, "default", None)
    if field_default is not None and field_default != models.fields.NOT_PROVIDED:
        return False

    if is_many_to_many and getattr(field, "blank", False):
        return False

    return not field.null


def convert_choice_name(name):
    name = to_const(force_str(name))
    try:
        assert_valid_name(name)
    except AssertionError:
        name = "A_%s" % name
    return name


def get_choices(choices):
    converted_names = []
    for value, help_text in choices:
        if isinstance(help_text, (tuple, list)):
            for choice in get_choices(help_text):
                yield choice
        else:
            name = convert_choice_name(value)
            while name in converted_names:
                name += "_" + str(len(converted_names))
            converted_names.append(name)
            description = help_text
            yield name, value, description


def convert_choices_field(field, choices, required=None):
    meta = field.model._meta
    name = to_camel_case("{}_{}".format(meta.object_name, field.name))
    choices = list(get_choices(choices))
    named_choices = [(c[0], c[1]) for c in choices]
    named_choices_descriptions = {c[0]: c[2] for c in choices}

    class EnumWithDescriptionsType(object):
        @property
        def description(self):
            return named_choices_descriptions[self.name]

    enum = Enum(name, list(named_choices), type=EnumWithDescriptionsType)
    # Note that we do not instantiate the field here, so we can store it un-instantiated in the registry.
    # This is the allow different parameters (e.g. `required`) to be passed to the field.
    return enum
    # return enum(description=field.help_text, required=is_required(field, required))


def convert_django_field_with_choices(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    choices = getattr(field, "choices", None)
    if choices:
        registry_name = to_camel_case(
            "{}_{}".format(field.model._meta.object_name, field.name)
        )
        # Fetch this from registry, if exists. We don't want to duplicate enum fields.
        enum = None
        if registry:
            from_registry = registry.get_converted_field(field)
            if from_registry:
                from_registry.kwargs['description'] = field.help_text
                from_registry.kwargs['required'] = is_required(field, required)
                return from_registry

        converted = convert_choices_field(field, choices, required)
        # Register enum fields
        if registry:
            registry.register_converted_field(registry_name, converted)
        return converted(
            description=field.help_text, required=is_required(field, required)
        )
    else:
        converted = convert_django_field_to_input(
            field,
            registry,
            required,
            field_many_to_many_extras,
            field_foreign_key_extras,
            field_one_to_one_extras,
        )
    return converted


@singledispatch
def convert_django_field_to_input(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    raise Exception(
        "Don't know how to convert the Django field %s (%s)" % (field, field.__class__)
    )


@convert_django_field_to_input.register(models.CharField)
@convert_django_field_to_input.register(models.TextField)
@convert_django_field_to_input.register(models.EmailField)
@convert_django_field_to_input.register(models.SlugField)
@convert_django_field_to_input.register(models.URLField)
@convert_django_field_to_input.register(models.GenericIPAddressField)
@convert_django_field_to_input.register(models.FilePathField)
def convert_field_to_string_extended(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return String(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.OneToOneField)
@convert_django_field_to_input.register(models.OneToOneRel)
def convert_one_to_one_field(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    type_name = (
        field_one_to_one_extras.get("type", "ID") if field_one_to_one_extras else "ID"
    )
    if type_name == "ID":
        return ID(
            description=getattr(field, "help_text", ""),
            required=is_required(field, required),
        )

    def dynamic_type():
        _type = registry.get_converted_field(type_name)

        if not _type:
            raise GraphQLError(f"The type {type_name} does not exist.")

        return InputField(
            _type,
            description=getattr(field, "help_text", ""),
            required=is_required(field, required),
        )

    return Dynamic(dynamic_type)


@convert_django_field_to_input.register(models.AutoField)
@convert_django_field_to_input.register(models.ForeignKey)
def convert_field_to_id(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    # Call getattr here, as OneToOneRel does not carry the attribute whatsoeever.
    id_type = ID(
        description=getattr(field, "help_text", ""),
        required=is_required(field, required),
    )
    _type_name = (field_foreign_key_extras or {}).get("type", "ID")
    if _type_name == "ID":
        return id_type

    # Use the Input type node from registry in a dynamic type, and create a union with that
    # and the ID
    def dynamic_type():

        _type = registry.get_converted_field(_type_name)

        if not _type:
            raise GraphQLError(f"The type {_type_name} does not exist.")

        return InputField(
            _type, description=field.help_text, required=is_required(field, required)
        )

    return Dynamic(dynamic_type)


@convert_django_field_to_input.register(models.UUIDField)
def convert_field_to_uuid(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return UUID(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.PositiveIntegerField)
@convert_django_field_to_input.register(models.PositiveSmallIntegerField)
@convert_django_field_to_input.register(models.SmallIntegerField)
@convert_django_field_to_input.register(models.BigIntegerField)
@convert_django_field_to_input.register(models.IntegerField)
def convert_field_to_int(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Int(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.BooleanField)
def convert_field_to_boolean(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    if is_required(field, required):
        return NonNull(Boolean, description=field.help_text)
    else:
        # This will only happen here if the field has a default
        return Boolean(description=field.help_text, required=False)


@convert_django_field_to_input.register(models.NullBooleanField)
def convert_field_to_nullboolean(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Boolean(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.FloatField)
def convert_field_to_float(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Float(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.DecimalField)
def convert_field_to_decimal(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Decimal(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.DurationField)
def convert_field_to_time_delta(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return TimeDelta(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.DateTimeField)
def convert_datetime_to_string(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    # We only render DateTimeFields with auto_now[_add] if they are explicitly required or not
    if required is None and (
        getattr(field, "auto_now", None) or getattr(field, "auto_now_add", None)
    ):
        return

    return DateTime(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.DateField)
def convert_date_to_string(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    # We only render DateFields with auto_now[_add] if they are explicitly required or not
    if required is None and (
        getattr(field, "auto_now", None) or getattr(field, "auto_now_add", None)
    ):
        return

    return Date(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.TimeField)
def convert_time_to_string(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Time(description=field.help_text, required=is_required(field, required))


@convert_django_field_to_input.register(models.ManyToManyField)
@convert_django_field_to_input.register(models.ManyToManyRel)
@convert_django_field_to_input.register(models.ManyToOneRel)
def convert_many_to_many_field(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    # Use getattr on help_text here as ManyToOnRel does not possess this.
    list_id_type = List(
        ID,
        description=getattr(field, "help_text", ""),
        required=is_required(field, required, True),
    )
    _type_name = (field_many_to_many_extras or {}).get("type", "ID")
    if _type_name == "ID":
        return list_id_type

    # Use the Input type node from registry in a dynamic type, and create a union with that
    # and the ID
    def dynamic_type():
        _type = registry.get_converted_field(_type_name)

        if not _type:
            raise GraphQLError(f"The type {_type_name} does not exist.")

        return List(
            _type,
            description=getattr(field, "help_text", ""),
            required=is_required(field, required, True),
        )

    return Dynamic(dynamic_type)


@convert_django_field_to_input.register(ArrayField)
def convert_postgres_array_to_list(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    base_type = convert_django_field_to_input(field.base_field)
    if not isinstance(base_type, (List, NonNull)):
        base_type = type(base_type)
    return List(
        base_type, description=field.help_text, required=is_required(field, required)
    )


@convert_django_field_to_input.register(HStoreField)
@convert_django_field_to_input.register(JSONField)
def convert_posgres_field_to_string(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return JSONString(
        description=field.help_text, required=is_required(field, required)
    )


@convert_django_field_to_input.register(RangeField)
def convert_postgres_range_to_string(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    inner_type = convert_django_field_to_input(field.base_field)
    if not isinstance(inner_type, (List, NonNull)):
        inner_type = type(inner_type)
    return List(
        inner_type, description=field.help_text, required=is_required(field, required)
    )


@convert_django_field_to_input.register(FileField)
@convert_django_field_to_input.register(ImageField)
def convert_file_field_to_upload(
    field,
    registry=None,
    required=None,
    field_many_to_many_extras=None,
    field_foreign_key_extras=None,
    field_one_to_one_extras=None,
):
    return Upload(required=is_required(field, required))
