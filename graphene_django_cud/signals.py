from django.dispatch import Signal

post_create_mutation = Signal()
post_update_mutation = Signal()
post_delete_mutation = Signal()

post_batch_create_mutation = Signal()
post_batch_update_mutation = Signal()
post_batch_delete_mutation = Signal()

post_filter_update_mutation = Signal()
post_filter_delete_mutation = Signal()
