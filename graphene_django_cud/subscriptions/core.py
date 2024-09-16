import graphene
from graphql import GraphQLError


class SubscriptionField(graphene.Field):
    """
    This is an extension of the graphene.Field class that exists
    to allow our DjangoCudSubscriptionBase classes to pass a subscribe
    method to the Field instantiation, which we use here in the
    `wrap_subscribe` method. `wrap_subscribe` is called internally in graphene
    to figure out which resolver to use for a subscription field.
    """

    def __init__(self, *args, subscribe=None, **kwargs):
        self.subscribe = subscribe
        super().__init__(*args, **kwargs)

    def wrap_subscribe(self, parent_subscribe):
        return self.subscribe


class DjangoCudSubscriptionBase(graphene.ObjectType):
    """Base class for DjangoCud subscriptions"""

    @classmethod
    def get_permissions(cls, root, info, *args, **kwargs):
        return cls._meta.permissions

    @classmethod
    def check_permissions(cls, root, info, *args, **kwargs) -> None:
        get_permissions = getattr(cls, "get_permissions", None)
        if not callable(get_permissions):
            raise TypeError("The `get_permissions` attribute of a subscription must be callable.")

        permissions = cls.get_permissions(root, info, *args, **kwargs)

        if permissions and len(permissions) > 0:
            if not info.context.user.has_perms(permissions):
                raise GraphQLError("Not permitted to access this subscription.")

    @classmethod
    def Field(cls, name=None, description=None, deprecation_reason=None, required=False):
        """Create a field for the subscription that automatically creates a subscription resolver"""
        return SubscriptionField(
            cls._meta.output,
            resolver=cls._meta.resolver,
            subscribe=cls._meta.subscribe,
            name=name,
            description=description or cls._meta.description,
            deprecation_reason=deprecation_reason,
            required=required,
        )

    @classmethod
    async def subscribe(cls, *args, **kwargs):
        """Dummy subscribe method. Must be implemented by subclasses"""
        raise NotImplementedError("`subscribe` must be implemented by the implementing subclass. "
                                  "This is likely a bug in graphene-django-cud.")
