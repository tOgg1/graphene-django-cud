import asyncio
from collections import OrderedDict

import graphene
from asgiref.sync import async_to_sync
from django.conf import settings
from django.db.models.signals import post_save
from graphene.types.objecttype import ObjectTypeOptions
from graphene_django.registry import get_global_registry

from graphene_django_cud.consts import USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS_KEY
from graphene_django_cud.signals import post_update_mutation
from graphene_django_cud.subscriptions.core import DjangoCudSubscriptionBase
from graphene_django_cud.util import to_snake_case


class DjangoUpdateSubscriptionOptions(ObjectTypeOptions):
    model = None
    return_field_name = None
    permissions = None
    signal = None


class DjangoUpdateSubscription(DjangoCudSubscriptionBase):
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
            signal=post_update_mutation if getattr(
                settings,
                USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS_KEY,
                False
            ) else post_save,
            **kwargs,
    ):
        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)

        if not _meta:
            _meta = DjangoUpdateSubscriptionOptions(cls)

        if not return_field_name:
            return_field_name = to_snake_case(model.__name__)

        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(model_type)

        _meta.model = model
        _meta.model_type = model_type
        _meta.fields = output_fields
        _meta.output = cls
        _meta.permissions = permissions

        # Importantly, this needs to be set to either nothing or the identity.
        # Internally in graphene it will be defaulted to the identity function. If it
        # isn't, graphene will try to pass the value resolve from the "subscribe" method
        # through this resolver. If it is also set to "subscribe", we will get an issue with
        # graphene trying to return an AsyncIterator.
        _meta.resolver = None

        # This is set to be the subscription resolver in the SubscriptionField class.
        _meta.subscribe = cls.subscribe
        _meta.return_field_name = return_field_name

        # Connect to the model's post_save (or your custom) signal
        signal.connect(cls._model_updated_handler, sender=model)

        super().__init_subclass_with_meta__(_meta=_meta, **kwargs)

    @classmethod
    def _model_updated_handler(cls, sender, instance, created=None, **kwargs):
        """Handle model updating and notify subscribers"""

        if created is not None and not created:
            return

        new_instance = cls.handle_object_updated(sender, instance, **kwargs)

        assert new_instance is None or isinstance(new_instance, cls._meta.model)

        if new_instance:
            instance = new_instance

        # Notify all subscribers for the model
        for subscriber in cls.subscribers.get(sender, []):
            async_to_sync(subscriber)(instance)

    @classmethod
    def handle_object_updated(cls, sender, instance, **kwargs):
        """Handle and modify any instance created"""
        pass

    @classmethod
    def check_permissions(cls, root, info, *args, **kwargs) -> None:
        return super().check_permissions(root, info, *args, **kwargs)

    @classmethod
    async def subscribe(cls, root, info, *args, **kwargs):
        """Subscribe to the model update events asynchronously"""

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
                # Wait for the next model instance to be updated
                instance = await queue.get()
                data = {cls._meta.return_field_name: instance}
                yield cls(**data)
        finally:
            # Clean up the subscriber when the subscription ends
            cls.subscribers[model].remove(queue.put)
