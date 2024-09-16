import asyncio
from collections import OrderedDict
from typing import Optional

import graphene
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save, post_delete
from graphene.types.objecttype import ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene_django.registry import get_global_registry
from requests import delete

from graphene_django_cud.subscriptions.core import DjangoCudSubscriptionBase
from graphene_django_cud.util import to_snake_case

from graphene_django_cud.util.dict import get_any_of
import logging

logger = logging.getLogger(__name__)


class DjangoDeleteSubscriptionOptions(ObjectTypeOptions):
    model = None
    return_field_name = None
    permissions = None
    signal = None


class DjangoDeleteSubscription(DjangoCudSubscriptionBase):
    # All active subscriptions are stored in this centralized dictionary.
    # We need to do this to keep track of which subscriptions are listening to
    # which signals.
    subscribers = {}

    @classmethod
    def __init_subclass_with_meta__(
            cls,
            _meta=None,
            model=None,
            permissions=None,
            return_field_name=None,
            signal=post_delete,
            **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        if not _meta:
            _meta = DjangoDeleteSubscriptionOptions(cls)

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        output_fields = OrderedDict()
        output_fields["id"] = graphene.String()

        _meta.model = model
        _meta.model_type = model_type
        _meta.fields = yank_fields_from_attrs(output_fields, _as=graphene.Field)
        _meta.output = cls
        _meta.permissions = permissions

        # Importantly, this needs to be set to either nothing or the identity.
        # Internally in graphene it will be defaulted to the identity function.
        _meta.resolver = None

        # This is set to be the subscription resolver in the SubscriptionField class.
        _meta.subscribe = cls.subscribe
        _meta.return_field_name = return_field_name

        # Connect to the model's post_save signal
        signal.connect(cls._model_deleted_handler, sender=model)

        super().__init_subclass_with_meta__(_meta=_meta, **kwargs)

    @classmethod
    def _model_deleted_handler(cls, sender, *args, **kwargs):
        """Handle model updating and notify subscribers"""

        Model = cls._meta.model

        instance: Optional[Model] = kwargs.get("instance", None) or next(filter(
            lambda x: isinstance(x, Model), args
        ), None)

        deleted_id = get_any_of(
            kwargs,
            [
                "pk",
                "raw_id",
                "input_id",
                "id"
            ]
        ) if not instance else get_any_of(
            instance,
            [
                "pk",
                "id",
            ]
        )

        if deleted_id is None:
            logger.warning("Received a delete signal for a model without an instance or an id being passed to the "
                           "signal handler. Are you using a compatible signal? Read the documentation for "
                           "graphene-django-cud for more information.")
            return

        new_deleted_id = cls.handle_object_deleted(sender, deleted_id, **kwargs)

        if new_deleted_id is not None:
            deleted_id = new_deleted_id

        # Notify all subscribers for the model
        for subscriber in cls.subscribers.get(sender, []):
            async_to_sync(subscriber)(deleted_id)

    @classmethod
    def handle_object_deleted(cls, sender, deleted_id, **kwargs):
        """Handle and modify any instance created"""
        pass

    @classmethod
    def check_permissions(cls, root, info, *args, **kwargs) -> None:
        return super().check_permissions(root, info, *args, **kwargs)

    @classmethod
    async def subscribe(cls, root, info, *args, **kwargs):
        """Subscribe to the model creation events asynchronously"""

        cls.check_permissions(root, info, *args, **kwargs)

        model = cls._meta.model
        queue = asyncio.Queue()

        # Ensure there's a list of subscribers for the model
        if model not in cls.subscribers:
            cls.subscribers[model] = []

        # Add the queue's put method to the subscribers for this model
        cls.subscribers[model].append(queue.put)

        try:
            while True:
                # Wait for the next model instance to be deleted
                _id = await queue.get()

                yield cls(id=_id)
        finally:
            # Clean up the subscriber when the subscription ends
            cls.subscribers[model].remove(queue.put)
