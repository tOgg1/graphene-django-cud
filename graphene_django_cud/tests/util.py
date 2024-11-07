from graphene import Schema


def get_introspected_mutation(schema: Schema, name: str):
    introspected = schema.introspect()
    types = introspected.get("__schema", {}).get("types", [])
    mutation = next(filter(lambda t: t.get("name", None) == name, types), {})

    return mutation


def get_introspected_field(schema: Schema, mutation_name: str, field_name: str):
    introspected_mutation = get_introspected_mutation(schema, mutation_name)

    fields = introspected_mutation.get("fields", [])
    field = next(filter(lambda f: f.get("name", None) == field_name, fields), {})

    return field


def get_introspected_field_kind(schema: Schema, mutation_name: str, field_name: str):
    field = get_introspected_field(schema, mutation_name, field_name)
    kind = field.get("type", {}).get("kind", None)

    return kind


def get_introspected_list_field_item_kind(schema: Schema, mutation_name: str, field_name: str):
    field = get_introspected_field(schema, mutation_name, field_name)
    kind = field.get("type", {}).get("ofType", {}).get("ofType", {}).get("kind", None)

    return kind
