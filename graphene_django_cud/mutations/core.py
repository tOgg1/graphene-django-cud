from typing import Iterable, Union

from django.db import models
from graphene import Mutation
from graphene.types.mutation import MutationOptions
from graphql import GraphQLError

from graphene_django_cud.registry import get_type_meta_registry
from graphene_django_cud.util import (
    get_likely_operation_from_name,
    disambiguate_id,
    get_fk_all_extras_field_names,
    get_m2m_all_extras_field_names,
    disambiguate_ids,
    is_field_many_to_many,
    is_field_one_to_one,
    is_field_many_to_one, get_model_field_or_none,
)

meta_registry = get_type_meta_registry()


class DjangoCudBase(Mutation):
    class Meta:
        abstract = True

    @classmethod
    def get_or_create_foreign_obj(cls, field, value, data, info):
        field_type = data.get("type", "ID")

        if field_type == "ID":
            return value
        else:
            input_type_meta = meta_registry.get_meta_for_type(field_type)
            # Create new obj
            related_obj = cls.create_obj(
                value,
                info,
                input_type_meta.get("auto_context_fields", {}),
                input_type_meta.get("many_to_many_extras", {}),
                input_type_meta.get("foreign_key_extras", {}),
                input_type_meta.get("many_to_one_extras", {}),
                input_type_meta.get("one_to_one_extras", {}),
                field.related_model,
            )
            return related_obj.id

    @classmethod
    def create_or_update_one_to_one_relation(cls, obj, field, value, data, info):
        existing_value = getattr(obj, field.name, None)

        field_type = data.get("type")
        input_type_meta = meta_registry.get_meta_for_type(field_type)

        if not existing_value:
            return cls.create_obj(
                value,
                info,
                input_type_meta.get("auto_context_fields", {}),
                input_type_meta.get("many_to_many_extras", {}),
                input_type_meta.get("foreign_key_extras", {}),
                input_type_meta.get("many_to_one_extras", {}),
                input_type_meta.get("one_to_one_extras", {}),
                field.related_model,
            )
        else:
            obj = cls.update_obj(
                existing_value,
                value,
                info,
                input_type_meta.get("auto_context_fields", {}),
                input_type_meta.get("many_to_many_extras", {}),
                input_type_meta.get("foreign_key_extras", {}),
                input_type_meta.get("many_to_one_extras", {}),
                input_type_meta.get("one_to_one_extras", {}),
                field.related_model,
            )
            obj.save()
            return obj

    @classmethod
    def get_or_create_m2m_objs(cls, field, values, data, operation, info):
        results = []

        if not values:
            return results

        if isinstance(data, bool):
            data = {}

        field_type = data.get("type", "ID")

        for value in values:
            if field_type == "ID":
                related_obj = field.related_model.objects.get(pk=cls.resolve_id(value))
            else:
                # This is something that we are going to create
                input_type_meta = meta_registry.get_meta_for_type(field_type)
                # Create new obj
                related_obj = cls.create_obj(
                    value,
                    info,
                    {
                        **input_type_meta.get("auto_context_fields", {}),
                        **data.get("auto_context_fields", {})
                    },
                    {
                        **input_type_meta.get("many_to_many_extras", {}),
                        **data.get("many_to_many_extras", {})
                    },
                    {
                        **input_type_meta.get("foreign_key_extras", {}),
                        **data.get("foreign_key_extras", {})
                    },
                    {
                        **input_type_meta.get("many_to_one_extras", {}),
                        **data.get("many_to_one_extras", {})
                    },
                    {
                        **input_type_meta.get("one_to_one_extras", {}),
                        **data.get("one_to_one_extras", {})
                    },
                    field.related_model,
                )
            results.append(related_obj)

        return results

    @classmethod
    def get_or_upsert_m2o_objs(cls, obj, field, values, data, operation, info, Model):
        results = []

        if not values:
            return results

        field_type = data.get("type", "auto")
        for value in values:
            if field_type == "ID":
                related_obj = field.related_model.objects.get(
                    pk=cls.resolve_id(value))
                results.append(related_obj)
            else:
                input_type_meta = meta_registry.get_meta_for_type(field_type)
                auto_context_fields = {
                    **input_type_meta.get("auto_context_fields", {}),
                    **data.get("auto_context_fields", {})
                }
                many_to_many_extras = {
                    **input_type_meta.get("many_to_many_extras", {}),
                    **data.get("many_to_many_extras", {})
                }
                foreign_key_extras = {
                    **input_type_meta.get("foreign_key_extras", {}),
                    **data.get("foreign_key_extras", {})
                }
                many_to_one_extras = {
                    **input_type_meta.get("many_to_one_extras", {}),
                    **data.get("many_to_one_extras", {})
                }
                one_to_one_extras = {
                    **input_type_meta.get("one_to_one_extras", {}),
                    **data.get("one_to_one_extras", {})
                }

                if field_type == "auto":
                    # In this case, a new type has been created for us. Let's first find it's name,
                    # then get it's meta, and then create it. We also need to attach the obj as the
                    # foreign key.
                    _type_name = data.get(
                        "type_name",
                        f"{operation.capitalize()}{Model.__name__}{field.name.capitalize()}",
                    )

                    # Ensure the parent relation exists and has the correct id.
                    value[field.field.name] = obj.id

                    # We use upsert here, as the operation might be "update", where we
                    # want to update the object.
                    related_obj = cls.upsert_obj(
                        value,
                        info,
                        auto_context_fields,
                        many_to_many_extras,
                        foreign_key_extras,
                        many_to_one_extras,
                        one_to_one_extras,
                        field.related_model,
                    )
                    results.append(related_obj)
                else:
                    # Create new obj
                    related_obj = cls.create_obj(
                        value,
                        info,
                        auto_context_fields,
                        many_to_many_extras,
                        foreign_key_extras,
                        many_to_one_extras,
                        one_to_one_extras,
                        field.related_model,
                    )
                    results.append(related_obj)

        return results

    @classmethod
    def get_all_objs(cls, Model, ids: Iterable[Union[str, int]]):
        """
        Helper method for getting a number of objects with Model.objects.get()
        :return:
        """
        objs = []
        for id in ids:
            objs.append(Model.objects.get(pk=cls.resolve_id(id)))

        return objs

    @classmethod
    def upsert_obj(
        cls,
        input,
        info,
        auto_context_fields,
        many_to_many_extras,
        foreign_key_extras,
        many_to_one_extras,
        one_to_one_extras,
        Model,
    ):
        id = cls.resolve_id(input.get("id"))
        obj = Model.objects.filter(pk=id).first()

        if obj:
            obj = cls.update_obj(
                obj,
                input,
                info,
                auto_context_fields,
                many_to_many_extras,
                foreign_key_extras,
                many_to_one_extras,
                one_to_one_extras,
                Model,
            )
            obj.save()
            return obj
        else:
            return cls.create_obj(
                input,
                info,
                auto_context_fields,
                many_to_many_extras,
                foreign_key_extras,
                many_to_one_extras,
                one_to_one_extras,
                Model,
            )

    @classmethod
    def create_obj(
        cls,
        input,
        info,
        auto_context_fields,
        many_to_many_extras,
        foreign_key_extras,
        many_to_one_extras,
        one_to_one_extras,
        Model,
    ):
        meta_registry = get_type_meta_registry()

        many_to_many_to_add = {}
        many_to_many_to_remove = {}
        many_to_many_to_set = {}
        many_to_one_to_add = {}
        many_to_one_to_remove = {}
        many_to_one_to_set = {}
        model_field_values = {}
        one_to_one_rels = {}

        many_to_many_extras_field_names = get_m2m_all_extras_field_names(
            many_to_many_extras
        )
        # The layout is the same as for m2m
        many_to_one_extras_field_names = get_m2m_all_extras_field_names(
            many_to_one_extras
        )
        foreign_key_extras_field_names = get_fk_all_extras_field_names(
            foreign_key_extras
        )

        for field_name, context_name in auto_context_fields.items():
            if hasattr(info.context, context_name):
                model_field_values[field_name] = getattr(info.context, context_name)

        for name, value in super(type(input), input).items():
            # Handle these separately
            if (
                name in many_to_many_extras_field_names
                or name in foreign_key_extras_field_names
                or name in many_to_one_extras_field_names
            ):
                continue

            field = get_model_field_or_none(name, Model)

            # Custom fields are not handled here
            if field is None:
                continue

            new_value = value

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_many = is_field_many_to_many(field)

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_one = is_field_many_to_one(field)

            # We cannot handle nested one to one rels before we have saved.
            if type(field) == models.OneToOneRel and not (
                # This case happens if the one to one field is specified as a related id.
                isinstance(value, str)
                or isinstance(value, int)
            ):
                one_to_one_rels[name] = value
                continue

            value_handle_name = "handle_" + name
            if hasattr(cls, value_handle_name):
                handle_func = getattr(cls, value_handle_name)
                assert callable(
                    handle_func
                ), f"Property {value_handle_name} on {cls.__name__} is not a function."
                new_value = handle_func(value, name, info)

            # On some fields we perform some default conversion, if the value was not transformed above.
            if new_value == value and value is not None:
                if isinstance(field, models.AutoField):
                    new_value = cls.resolve_id(value)
                # The order here is important
                elif isinstance(field, models.OneToOneField):
                    # If the value is an integer or a string, we assume it is an ID
                    if isinstance(value, str) or isinstance(value, int):
                        name = getattr(field, "db_column", None) or name + "_id"
                        new_value = cls.resolve_id(value)
                    else:
                        # We can use create obj directly here, as we know the foreign object does
                        # not already exist.
                        extra_data = one_to_one_extras.get(name, {})

                        new_value = cls.create_obj(
                            value,
                            info,
                            extra_data.get("auto_context_fields", {}),
                            extra_data.get("many_to_many_extras", {}),
                            extra_data.get("foreign_key_extras", {}),
                            extra_data.get("many_to_one_extras", {}),
                            extra_data.get("one_to_one_extras", {}),
                            field.related_model,
                        )
                elif isinstance(field, models.OneToOneRel) or isinstance(
                    field, models.ForeignKey
                ):
                    # Delete auto context field here, if it exists. We have to do this explicitly
                    # as we change the name below
                    if name in auto_context_fields:
                        del model_field_values[name]

                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = cls.resolve_id(value)
                elif field_is_many_to_many:
                    new_value = cls.resolve_ids(value)

            if field_is_many_to_many:
                many_to_many_to_set[name] = cls.get_all_objs(field.related_model, new_value)
            elif field_is_many_to_one:
                many_to_one_to_set[name] = cls.get_all_objs(field.related_model, new_value)
            else:
                model_field_values[name] = new_value

        # We don't have an object yet, and we potentially need to create
        # parents before proceeding.
        for name, extras in foreign_key_extras.items():
            value = input.get(name, None)
            field = Model._meta.get_field(name)

            obj_id = cls.get_or_create_foreign_obj(field, value, extras, info)

            model_field_values[name + "_id"] = obj_id

        # Foreign keys are added, we are ready to create our object
        obj = Model.objects.create(**model_field_values)

        # Handle one to one rels
        if len(one_to_one_rels) > 0:

            for name, value in one_to_one_rels.items():
                field = Model._meta.get_field(name)
                new_value = value

                value_handle_name = "handle_" + name
                if hasattr(cls, value_handle_name):
                    handle_func = getattr(cls, value_handle_name)
                    assert callable(
                        handle_func
                    ), f"Property {value_handle_name} on {cls.__name__} is not a function."
                    new_value = handle_func(value, name, info)

                # Value was not transformed
                if new_value == value:
                    # If the value is an integer or a string, we assume it is an ID
                    if isinstance(value, str) or isinstance(value, int):
                        name = getattr(field, "db_column", None) or name + "_id"
                        new_value = cls.resolve_id(value)
                    else:
                        extra_data = one_to_one_extras.get(name, {})

                        # This is a nested field we need to take care of.
                        value[field.field.name] = obj.id
                        new_value = cls.create_or_update_one_to_one_relation(
                            obj, field, value, extra_data, info
                        )

                setattr(obj, name, new_value)

            obj.save()

        # Handle extras fields
        for name, extras in many_to_many_extras.items():
            field = Model._meta.get_field(name)
            if not name in many_to_many_to_add:
                many_to_many_to_add[name] = []
                many_to_many_to_remove[name] = []
                many_to_many_to_set[
                    name
                ] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if isinstance(data, bool):
                    data = {}

                operation = data.get("operation") or get_likely_operation_from_name(
                    extra_name
                )
                objs = cls.get_or_create_m2m_objs(field, values, data, operation, info)

                if operation == "exact":
                    many_to_many_to_set[name] = objs
                elif len(objs) > 0:
                    if operation == "add":
                        many_to_many_to_add[name] += objs
                    else:
                        many_to_many_to_remove[name] += objs

        for name, extras in many_to_one_extras.items():
            field = Model._meta.get_field(name)

            if not name in many_to_one_to_add:
                many_to_one_to_add[name] = []
                many_to_one_to_remove[name] = []
                many_to_one_to_set[
                    name
                ] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if values is None:
                    continue

                if isinstance(data, bool):
                    data = {}

                operation = data.get("operation") or get_likely_operation_from_name(
                    extra_name
                )

                if operation == "exact":
                    objs = cls.get_or_upsert_m2o_objs(
                        obj, field, values, data, operation, info, Model
                    )
                    many_to_one_to_set[name] = objs
                elif operation == "add" or operation == "update":
                    objs = cls.get_or_upsert_m2o_objs(
                        obj, field, values, data, operation, info, Model
                    )
                    many_to_one_to_add[name] += objs
                else:
                    many_to_one_to_remove[name] += cls.resolve_ids(values)

        for name, objs in many_to_one_to_set.items():
            if objs is not None:
                field = getattr(obj, name)
                if hasattr(field, "remove"):
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
            if hasattr(field, "remove"):
                # The field is nullable, and we simply remove the relation
                related_name = Model._meta.get_field(name).remote_field.name
                getattr(obj, name).filter(id__in=objs).update(**{related_name: None})
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
        one_to_one_extras,
        Model,
    ):

        many_to_many_to_add = {}
        many_to_many_to_remove = {}
        many_to_many_to_set = {}
        many_to_one_to_add = {}
        many_to_one_to_remove = {}
        many_to_one_to_set = {}

        many_to_many_extras_field_names = get_m2m_all_extras_field_names(
            many_to_many_extras
        )
        many_to_one_extras_field_names = get_m2m_all_extras_field_names(
            many_to_one_extras
        )  # The layout is the same as for m2m
        foreign_key_extras_field_names = get_fk_all_extras_field_names(
            foreign_key_extras
        )

        for field_name, context_name in auto_context_fields.items():
            if hasattr(info.context, context_name):
                setattr(obj, field_name, getattr(info.context, context_name))

        for name, value in super(type(input), input).items():
            # Handle these separately
            if (
                name in many_to_many_extras_field_names
                or name in foreign_key_extras_field_names
                or name in many_to_one_extras_field_names
            ):
                continue

            field = get_model_field_or_none(name, Model)

            # Custom fields are not handled here
            if field is None:
                continue

            new_value = value

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_many = is_field_many_to_many(field)

            # We have to handle this case specifically, by using the fields
            # .set()-method, instead of direct assignment
            field_is_many_to_one = is_field_many_to_one(field)

            field_is_one_to_one = is_field_one_to_one(field)

            value_handle_name = "handle_" + name
            if hasattr(cls, value_handle_name):
                handle_func = getattr(cls, value_handle_name)
                assert callable(
                    handle_func
                ), f"Property {value_handle_name} on {cls.__name__} is not a function."
                new_value = handle_func(value, name, info)

            # On some fields we perform some default conversion, if the value was not transformed above.
            if new_value == value and value is not None:
                if isinstance(field, models.AutoField):
                    new_value = cls.resolve_id(value)
                elif isinstance(field, models.OneToOneField):
                    # If the value is an integer or a string, we assume it is an ID
                    if isinstance(value, str) or isinstance(value, int):
                        name = getattr(field, "db_column", None) or name + "_id"
                        new_value = cls.resolve_id(value)
                    else:
                        extra_data = one_to_one_extras.get(name, {})
                        # This is a nested field we need to take care of.
                        value[field.remote_field.name] = obj.id
                        new_value = cls.create_or_update_one_to_one_relation(
                            obj, field, value, extra_data, info
                        )
                elif isinstance(field, models.OneToOneRel):
                    # If the value is an integer or a string, we assume it is an ID
                    if isinstance(value, str) or isinstance(value, int):
                        name = getattr(field, "db_column", None) or name + "_id"
                        new_value = cls.resolve_id(value)
                    else:
                        extra_data = one_to_one_extras.get(name, {})
                        # This is a nested field we need to take care of.
                        value[field.field.name] = obj.id
                        new_value = cls.create_or_update_one_to_one_relation(
                            obj, field, value, extra_data, info
                        )
                elif isinstance(field, models.ForeignKey):
                    # Delete auto context field here, if it exists. We have to do this explicitly
                    # as we change the name below
                    if name in auto_context_fields:
                        setattr(obj, name, None)

                    name = getattr(field, "db_column", None) or name + "_id"
                    new_value = cls.resolve_id(value)
                elif field_is_many_to_many:
                    new_value = cls.resolve_ids(value)

            if field_is_many_to_many:
                many_to_many_to_set[name] = cls.get_all_objs(field.related_model, new_value)
            elif field_is_many_to_one:
                many_to_one_to_set[name] = cls.get_all_objs(field.related_model, new_value)
            else:
                setattr(obj, name, new_value)

        # Handle extras fields
        for name, extras in foreign_key_extras.items():
            value = input.get(name, None)
            field = Model._meta.get_field(name)

            obj_id = cls.get_or_create_foreign_obj(field, value, extras, info)
            setattr(obj, name + "_id", obj_id)

        for name, extras in many_to_many_extras.items():
            field = Model._meta.get_field(name)
            if not name in many_to_many_to_add:
                many_to_many_to_add[name] = []
                many_to_many_to_remove[name] = []
                many_to_many_to_set[
                    name
                ] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if isinstance(data, bool):
                    data = {}

                operation = data.get("operation") or get_likely_operation_from_name(
                    extra_name
                )
                objs = cls.get_or_create_m2m_objs(field, values, data, operation, info)

                if operation == "exact":
                    many_to_many_to_set[name] = objs
                elif operation == "add":
                    many_to_many_to_add[name] += objs
                else:
                    many_to_many_to_remove[name] += objs

        for name, extras in many_to_one_extras.items():
            field = Model._meta.get_field(name)

            if not name in many_to_one_to_add:
                many_to_one_to_add[name] = []
                many_to_one_to_remove[name] = []
                many_to_one_to_set[
                    name
                ] = None  # None means that we should not (re)set the relation.

            for extra_name, data in extras.items():
                field_name = name
                if extra_name != "exact":
                    field_name = name + "_" + extra_name

                values = input.get(field_name, None)

                if values is None:
                    continue

                if isinstance(data, bool):
                    data = {}

                operation = data.get("operation") or get_likely_operation_from_name(
                    extra_name
                )

                if operation == "exact":
                    objs = cls.get_or_upsert_m2o_objs(
                        obj, field, values, data, operation, info, Model
                    )
                    many_to_one_to_set[name] = objs
                elif operation == "add" or operation == "update":
                    objs = cls.get_or_upsert_m2o_objs(
                        obj, field, values, data, operation, info, Model
                    )
                    many_to_one_to_add[name] += objs
                else:
                    many_to_one_to_remove[name] += cls.resolve_ids(values)

        for name, objs in many_to_one_to_set.items():
            if objs is not None:
                field = getattr(obj, name)
                if hasattr(field, "remove"):
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
            if hasattr(field, "remove"):
                # The field is nullable, and we simply remove the relation
                related_name = Model._meta.get_field(name).remote_field.name
                getattr(obj, name).filter(id__in=objs).update(**{related_name: None})
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
        get_permissions = getattr(cls, "get_permissions", None)
        if not callable(get_permissions):
            raise TypeError(
                "The `get_permissions` attribute of a mutation must be callable."
            )

        permissions = cls.get_permissions(root, info, *args, **kwargs)

        if permissions and len(permissions) > 0:
            if not info.context.user.has_perms(permissions):
                raise GraphQLError("Not permitted to access this mutation.")

    @classmethod
    def validate(cls, root, info, input, *args, **kwargs):
        for name, value in super(type(input), input).items():
            validate_field_name = f"validate_{name}"
            validate_field = getattr(cls, validate_field_name, None)

            if validate_field and callable(validate_field):
                validate_field(root, info, value, input, *args, **kwargs)

    @classmethod
    def before_mutate(cls, root, info, *args, **kwargs):
        return None

    @classmethod
    def before_save(cls, root, info, *args, **kwargs):
        return None

    @classmethod
    def after_mutate(cls, root, info, *args, **kwargs):
        return None

    @classmethod
    def resolve_id(cls, id):
        return disambiguate_id(id)

    @classmethod
    def resolve_ids(cls, ids):
        return disambiguate_ids(ids)


class DjangoCudBaseOptions(MutationOptions):
    model = None

    only_fields = None
    exclude_fields = None
    optional_fields = None
    required_fields = None
    auto_context_fields = None

    permissions = None
    login_required = None

    type_name = None
    return_field_name = None

    many_to_many_extras = None
    many_to_one_extras = None
    foreign_key_extras = None
    one_to_one_extras = None

    field_types = None

    custom_fields = None
