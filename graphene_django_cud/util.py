from collections import OrderedDict

from graphene_django.utils import get_model_fields
from graphql_relay import from_global_id
from typing import Union

from graphene_django_cud.converter import convert_django_field_with_choices


def disambiguate_id(ambiguous_id: Union[int, float, str]):
    """
    disambiguate_id takes an id which may either be an integer-parsable
    variable, either as a string or a number; or it might be a base64 encoded
    global relay value.

    The method then attempts to extract from this token the actual id.

    :return:
    """
    # First see if it is an integer, if so
    # it is definitely not a relay global id
    final_id = -1
    try:
        final_id = int(ambiguous_id)
        return final_id
    except ValueError:
        # Try global value
        (_, final_id) = from_global_id(ambiguous_id)
    finally:
        return final_id


def disambiguate_ids(ids):
    if not hasattr(ids, "__iter__"):
        return [disambiguate_id(ids)]
    return [disambiguate_id(_id) for _id in ids]


def get_input_fields_for_model(
        model, registry, only_fields, exclude_fields, optional_fields=(), required_fields=()
):
    model_fields = get_model_fields(model)

    fields = OrderedDict()
    for name, field in model_fields:
        # We ignore the primary key
        if getattr(field, "primary_key", False):
            continue

        is_not_in_only = only_fields and name not in only_fields
        # is_already_created = name in options.fields
        is_excluded = name in exclude_fields  # or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith("+")
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue

        required = None
        if name in optional_fields:
            required = False
        elif name in required_fields:
            required = True

        converted = convert_django_field_with_choices(field, registry, required)
        fields[name] = converted

    return fields


def get_all_optional_input_fields_for_model(
        model, registry, only_fields, exclude_fields
):
    model_fields = get_model_fields(model)

    fields = OrderedDict()
    for name, field in model_fields:
        # We ignore the primary key
        if getattr(field, "primary_key", False):
            continue

        is_not_in_only = only_fields and name not in only_fields
        # is_already_created = name in options.fields
        is_excluded = name in exclude_fields  # or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith("+")
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue

        converted = convert_django_field_with_choices(field, registry)
        # Override required
        converted.kwargs["required"] = False

        fields[name] = converted

    return fields

