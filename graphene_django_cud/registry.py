from graphene_django.registry import Registry


class TypeMetaRegistry:
    """
    TypeMetaRegistry is used to lookup meta-data for Types. In particular, this is
    used to make sure we can reuse information such as auto-context-fields, optional-fields,
    extras, etc.
    """

    def __init__(self):
        self._registry = {}

    def register(self, type, meta):
        assert isinstance(meta, dict)

        if isinstance(type, str):
            self._registry[type] = meta
        else:
            self._registry[type.__name__] = meta

    def unregister(self, type):
        del self._registry[type]

    def get_meta_for_type(self, type):
        if isinstance(type, str):
            return self._registry.get(type, {})
        else:
            return self._registry.get(type.__name__, {})


input_type_registry = None
type_meta_registry = None


def get_input_registry():
    global input_type_registry
    if not input_type_registry:
        input_type_registry = Registry()
    return input_type_registry


def get_type_meta_registry():
    global type_meta_registry
    if not type_meta_registry:
        type_meta_registry = TypeMetaRegistry()
    return type_meta_registry
