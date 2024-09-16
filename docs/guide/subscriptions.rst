.. _subscriptions:
================================
Subscriptions
================================

*Subscriptions are still WIP. Consider the API to be unstable and the functionality to be experimental.*

Graphene-django-cud provides a number of subscriptions classes, which can be used to create subscriptions
for models.

The following subscriptions are currently available:

* ``DjangoCreateSubscription``
* ``DjangoUpdateSubscription``
* ``DjangoDeleteSubscription``
* ``DjangoSignalSubscription``

Getting started
------------------

There are multiple ways to set up subscriptions and async behaviour in Graphene. See the `Graphene documentation`_ for more information.

A simple alternative to the options above is to use `Graphene Luna`_, which uses the graphql-ws protocol.


Subscription classes
---------------------

DjangoCreateSubscription
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    class CatCreatedSubscription(DjangoCreateSubscription):
        class Meta:
            model = Cat
            signal = post_create_mutation
            permissions = ("tests.create_cat",)


    class Subscriptions(graphene.ObjectType):
        cat_created = CatCreatedSubscription.Field()


    schema = Schema(query=Query, mutation=Mutations, subscription=Subscriptions)


This will create a subscription that will be called whenever a new Cat is created. The subscription will be called with the newly created Cat object.

.. code:: json

    {
      "data": {
        "catUpdated": {
          "cat": {
            "id": "Q2F0Tm9kZTozNA==",
            "name": "fidus"
          }
        }
      }
    }

The `signal` attribute is optional. If not supplied it will default to `post_save`. When using the `post_create_mutation` signal above,
the subscription will only be called at the end of a CreateCatMutation.

See the caveats and intricacies to this listed below.

DjangoUpdateSubscription
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    class CatUpdatedSubscription(DjangoUpdateSubscription):
        class Meta:
            model = Cat
            signal = post_update_mutation
            permissions = ("tests.update_cat",)

    class Subscriptions(graphene.ObjectType):
        cat_updated = CatUpdatedSubscription.Field()

    schema = Schema(query=Query, mutation=Mutations, subscription=Subscriptions)

This will create a subscription that will be called whenever a Cat is updated. The subscription will be called with the updated Cat object.

.. code:: json

    {
      "data": {
        "catUpdated": {
          "cat": {
            "id": "Q2F0Tm9kZTozNA==",
            "name": "fidus"
          }
        }
      }
    }


DjangoDeleteSubscription
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    class CatDeletedSubscription(DjangoDeleteSubscription):
        class Meta:
            model = Cat
            signal = post_delete_mutation
            permissions = ("tests.delete_cat",)

    class Subscriptions(graphene.ObjectType):
        cat_deleted = CatDeletedSubscription.Field()

    schema = Schema(query=Query, mutation=Mutations, subscription=Subscriptions)

This will create a subscription that will be called whenever a Cat is deleted. The subscription will be called with the ID of the deleted Cat.

.. code:: json

    {
      "data": {
        "catDeleted": {
            "id": "Q2F0Tm9kZTozNA=="
        }
      }
    }


DjangoSignalSubscription
^^^^^^^^^^^^^^^^^^^^^^^^

This is a generic subscription class that can be used to hook into any Django signal and send some data back to the
subscribing client.

The structure of an implementation looks like this:is as follows:


.. code:: python

    some_signal = Signal()

    class SomeSignalSubscription(DjangoSignalSubscription):
        class Meta:
            signal = some_signal

        data_to_return = graphene.Int()

        @classmethod
        def transform_signal_data(cls, data):
            return {"data_to_return": data.get("some_field", 0)}

        class Meta:
            signal = test_signal


    class Subscriptions(graphene.ObjectType):
        subscribe_to_some_signal = SomeSignalSubscription.Field()

    schema = Schema(query=Query, mutation=Mutations, subscription=Subscriptions)

Then, in your code, you can send a signal like this:

.. code:: python

    some_signal.send(sender=MyClass, some_field=1337)


and receive the following:

.. code:: json

    {
      "data": {
        "subscribeToSomeSignal": {
          "dataToReturn": 1337
        }
      }
    }


There are a few important pieces to note here. The `transform_signal_data` method is used to transform the data
sent by the signal into the data that will be sent to the client. The returned data will be spread as kwargs into
the class constructor inside the deriving subscription class. So if you have say a class with the following fields:

.. code:: python

    class SomeOtherSignalSubscription(DjangoSignalSubscription):
        field_one = graphene.Int()
        field_two = graphene.String()

Then the `transform_signal_data` should return a dictionary with the following structure:

.. code:: json

    {
        "field_one": 1337,
        "field_two": "some_string"
    }


The argument `data` sent to the `transform_signal_data` method is a dictionary that is defined by spreading the
kwargs sent to the signal into the dictionary.

Handling nested fields and modifying signal data
-------------------------------------------------
The perhaps most important thing to note with the above subscriptions is that querying nested fields can't be done
"out-of-the-box". This is because subscriptions are called in an asynchronous context, while the Django ORM only works
in a synchronous context. When graphene starts traversing nested return data, for instance:

.. code:: graphql

    subscription {
        catUpdated{
            cat{
                id
                name
                owner{
                    id
                    name
                }
            }
        }
    }

it will at some point try to access the `owner` field of the `cat` object. This will fail, as the `owner` field is
not loaded by default, and a new database query will automagically be fired. This will fail as we are in an asynchronous
context.

To fix this, you currently have to explicitly preload all relations you want to access. This can be done in the
`handle_object_created` and `handle_object_updated` methods of the subscriptions. For instance:

.. code:: python

    class CatUpdatedSubscription(DjangoUpdateSubscription):
        class Meta:
            model = Cat
            signal = post_update_mutation
            permissions = ("tests.update_cat",)

        @classmethod
        def handle_object_updated(cls, sender, instance: Cat, *args, **kwargs):
            # This will load the owner object
            instance.owner


Alternatively, you can reload the object in question with the relevant amount of `select_releated` and  `prefetch_related`
calls to the queryset:


.. code:: python

    class CatUpdatedSubscription(DjangoUpdateSubscription):
        class Meta:
            model = Cat
            signal = post_update_mutation
            permissions = ("tests.update_cat",)

        @classmethod
        def handle_object_updated(cls, sender, instance: Cat, *args, **kwargs):
            cat = Cat.objects.select_related("owner").prefetch_related("enemies").get(pk=instance.pk)

            return cat


You can also use these methods to transform or manipulate the data in any way you like. Note that that handlers
are running in a synchronous context.


Library signals vs Django model signals
---------------------------------------

By default, the library will use the `post_save`/`post_delete` signal to send data to the client. This will make sure all signals from
any source are picked up.

However, this has the downside that it will fire multiple times for create and update mutations, as typically multiple
save calls are made during the course of an average mutation. The first of these calls will fire before the totality
of a mutation's effects have been applied. For instance, during a create mutation, the first `post_save` signal will be
fired before any many-to-one or many-to-many relations have been created. Hence, none of these relations will be
available to the client.

To handle this, you can use the :ref:`Library specific signals<signals>` instead, which will fire only when a mutation
is completed. The downside of this is that you will not pick up on general create/update/delete signals from other
sources, such as a DRF API.

Custom signals
--------------
If you want to consolidate all signals from all sources into a GCUD subscription, but still don't want to have the
issues with premature save signals, you should implement your own custom signals and pass these to the subscriptions.

For instance, for a create signal:

.. code:: python

    my_create_signal = Signal()

    class MyCreateSubscription(DjangoCreateSubscription):
        class Meta:
            model = Cat
            signal = my_create_signal


    def my_view(request):
        cat = Cat.objects.create(name="Fidus")
        my_create_signal.send(sender=Cat, instance=cat)
        return HttpResponse("OK")

If you want to hook signal up to the built in library signals, you can do this by chaining the signals:

.. code:: python

    my_create_signal = Signal()

    # Note that you need to make a proper new function here as an intermediary if the signal arguments
    # differ.
    post_create_mutation.connect(my_create_signal.send, sender=Cat)

You can in principle use any signal you want, but they need to send a specific set of arguments to function with
the subscription classes:

- `DjangoCreateSubscription`:
    - args: `sender` (added automatically), `instance`
    - kwargs: `created` (optional)
- `DjangoUpdateSubscription`:
    - args: `sender` (added automatically), `instance`
    - kwargs: `created` (optional)
- `DjangoDeleteSubscription`:
    - args: `sender` (added automatically)
    - kwargs: Either `instance` with at least the attribute `id` or `pk`; or one of the following kwargs: `pk`, `raw_id, `input_id`, `id`.

You can also override the method `_model_created_handler`, `_model_updated_handler` or `_model_deleted_handler` to handle signals.
Make sure you take a look at the current implementations of these to get an idea of how to call the subscriptions appropriately.


Using the library signals by default
---------------------------------------
You can enable the :ref:`library signals<signals>` globally (and by default), by adding the following to your settings:

.. code:: python

    GRAPHENE_DJANGO_CUD_USE_MUTATION_SIGNALS_FOR_SUBSCRIPTIONS = True




.. _Graphene documentation: https://docs.graphene-python.org/projects/django/en/latest/subscriptions/
.. _Graphene Luna: https://github.com/cognitive-space/graphene-luna
.. _Signals: https://docs.djangoproject.com/en/4.1/topics/signals/