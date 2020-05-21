from .batch_create import DjangoBatchCreateMutation
from .filter_delete import DjangoFilterDeleteMutation
from .create import DjangoCreateMutation
from .delete import DjangoDeleteMutation
from .patch import DjangoPatchMutation
from .update import DjangoUpdateMutation

__all__ = (
    'DjangoCreateMutation',
    'DjangoBatchCreateMutation',
    'DjangoPatchMutation',
    'DjangoUpdateMutation',
    'DjangoDeleteMutation',
    'DjangoFilterDeleteMutation',
)
