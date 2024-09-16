import asyncio
from typing import Optional

from asgiref.sync import async_to_sync
from django.dispatch import Signal
from graphene import Field
from graphene.types.objecttype import ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs

from graphene_django_cud.subscriptions.core import DjangoCudSubscriptionBase


class DjangoSignalSubscriptionOptions(ObjectTypeOptions):
    permissions = None
    signal: Optional[Signal] = None
    sender = None


class DjangoSignalSubscription(DjangoCudSubscriptionBase):
    subscribers = set()

    @classmethod
    def __init_subclass_with_meta__(
            cls,
            _meta=None,
            permissions=None,
            signal=None,
            sender=None,
            output=None,
            **kwargs,
    ):
        if not _meta:
            _meta = DjangoSignalSubscriptionOptions(cls)

        if not signal:
            raise ValueError("You must specify a signal to subscribe to")

        output = output or getattr(cls, "Output", None)

        if not output:
            # If output is defined, we don't need to get the fields
            fields = {}
            for base in reversed(cls.__mro__):
                fields.update(yank_fields_from_attrs(base.__dict__, _as=Field))
            output = cls

        _meta.permissions = permissions
        _meta.signal = signal
        _meta.output = output

        # Importantly, this needs to be set to either nothing or the identity.
        # Internally in graphene it will be defaulted to the identity function. If it
        # isn't, graphene will try to pass the value resolve from the "subscribe" method
        # through this resolver. If it is also set to "subscribe", we will get an issue with
        # graphene trying to return an AsyncIterator.
        _meta.resolver = None

        # This is set to be the subscription resolver in the SubscriptionField class.
        _meta.subscribe = cls.subscribe

        signal.connect(cls.handle_signal, sender=sender)

        super().__init_subclass_with_meta__(_meta=_meta, **kwargs)

    @classmethod
    def handle_signal(cls, *args, **kwargs):
        data_item = {
            **kwargs,
            "args": args,
        }
        for subscriber in cls.subscribers:
            async_to_sync(subscriber)(data_item)

    @classmethod
    def transform_signal_data(cls, data):
        """Transform data into the appropriate dictionary for the fields associated
        with this subscription"""
        raise NotImplementedError("`transform_signal_data` must be implemented by the implementing subclass.")

    @classmethod
    async def subscribe(cls, root, info, *args, **kwargs):
        """Subscribe to the model creation events asynchronously"""
        cls.check_permissions(root, info, *args, **kwargs)

        queue = asyncio.Queue()

        # Add the queue's put method to the subscribers for this model
        cls.subscribers.add(queue.put)

        try:
            while True:
                # Wait for the next signal to be fired.
                signal_data = await queue.get()
                data = cls.transform_signal_data(signal_data)
                yield cls(**data)
        finally:
            # Clean up the subscriber when the subscription ends
            cls.subscribers.remove(queue.put)
