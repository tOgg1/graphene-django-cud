================================
Signals
================================

The library fires a number of custom signals, which also can be used to hook into the flow of the mutations.

Currently, the following signals are available:

* ``post_create_mutation``
* ``post_update_mutation``
* ``post_delete_mutation``
* ``post_batch_create_mutation``
* ``post_batch_update_mutation``
* ``post_batch_delete_mutation``
* ``post_filter_update_mutation``
* ``post_filter_delete_mutation``

Theses signals have utility as the `post_save` signal in Django will


.. code:: python

    from graphene_django_cud.signals import post_create_mutation

    @post_create_mutation.connect
    def handle_post_create_mutation(sender, instance, created, **kwargs):
        print(f"A new instance of {sender} was created: {instance}")


The arguments passed to the signal handlers are:


- `´post_create_mutation´`:
    - sender: The Mutation class
    - instance: The instance that was created
- `´post_update_mutation´`:
    - sender: The Mutation class
    - instance: The instance that was updated
- `´post_delete_mutation´`:
    - sender: The Mutation class
    - id: The id of the instance that was deleted. This might be a global (relay ID) if you use relay. You can also override this by adding a `get_return_id` method to your mutation.
    - raw_id: The raw id of the instance that was deleted. This mirrors the model database id.
    - deleted_input_id: The id of the input that was used to delete the instance.
- `´post_batch_create_mutation´`:
    - sender: The Mutation class
    - instances: The instances that were created
- `´post_batch_update_mutation´`:
    - sender: The Mutation class
    - instances: The instances that were updated
- `´post_batch_delete_mutation´`:
    - sender: The Mutation class
    - ids: The ids of the instances that were deleted
    - deletion_count: The number of instances that were deleted
    - deleted_ids: The ids of the instances that were deleted. These can be overridden by adding a `get_return_id` method to your mutation.
- `´post_filter_update_mutation´`:
    - sender: The Mutation class
    - instances: A QuerySet of the instances that were updated
- `´post_filter_delete_mutation´`:
    - sender: The Mutation class
    - ids: The ids of the instances that were deleted.
