==============================
Auto context fields
==============================

The create, update and patch mutations contains a meta-field
``auto_context_fields``. It allows us to automatically assign field
values depending on values in the context (i.e. the current
``HttpRequest``). Most typically, this will be used to automatically
assign the the current user to some field.

Suppose for instance you have the following model:

.. code:: python

    class ForumThread(models.Model):
        created_by = models.ForeignKey(User, on_delete=models.CASCADE)

        # More fields

We can then automatically assign the created\_by field to the calling
user by creating a mutation:

.. code:: python

    class CreateForumThreadMutation(DjangoCreateMutation):
        class Meta:
            auto_context_fields = {
                'created_by': 'user'
            }

Presupposing, of course, that the ``user`` field of the ``info.context``
(HttpRequest) field is set. This works with any context field. Also note
that auto context fields are automatically set as ``required=False``, to
please Graphene. Finally note that if we add an explicit value to the
``createdBy`` field when calling the mutation, this value will override
the auto context field.
