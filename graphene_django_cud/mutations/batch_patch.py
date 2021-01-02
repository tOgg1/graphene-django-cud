

from graphene_django.utils import get_model_fields

from .batch_update import DjangoBatchUpdateMutation
from .core import DjangoCudBaseOptions


class DjangoBatchPatchMutationOptions(DjangoCudBaseOptions):
    pass


class DjangoBatchPatchMutation(DjangoBatchUpdateMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
            cls,
            _meta=None,
            model=None,
            optional_fields=None,
            type_name=None,
            **kwargs
    ):
        all_field_names = tuple(name for name, _ in get_model_fields(model))

        if optional_fields is None:
            optional_fields = all_field_names

        input_type_name = type_name or f"BatchPatch{model.__name__}Input"

        return super().__init_subclass_with_meta__(
            _meta=_meta,
            model=model,
            optional_fields=optional_fields,
            type_name=input_type_name,
            **kwargs
        )
