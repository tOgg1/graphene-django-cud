==============================
Overriding field types
==============================

*This section is primarily relevant for create, update and patch mutations.*

By default, graphene-django-cud iterates through all the fields of a model, and converts each field to a
corresponding graphene type. This converted type is added to the mutation input argument.

The conversions are typically what you would expect, e.g. ``models.CharField`` is converted to ``graphene.String``.

It is possible to override this conversion, by explicitly providing a **field_types** argument.
By default, the field will be coerced when added to the Django model instance. If the desired result is either
something more complex than a simple coercion, or the overriding type cannot be coerced into the corresponding
Django model field; then you must implement a :ref:`custom handler<custom_field_handling>`.


.. code-block:: python

    class Dog(models.Model):
        owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dogs')
        name = models.TextField()
        tag = models.CharField(max_length=16, default="Dog-1", help_text="Non-unique identifier for the dog, on the form 'Dog-%d'")


    class CreateDogMutation(DjangoCreateMutation):
        class Meta:
            model = Dog
            field_types = {
                "tag": graphene.Int(required=False)
            }

        @classmethod
        def handle_tag(cls, value, *args, **kwargs):
            return "Dog-" + str(value)


