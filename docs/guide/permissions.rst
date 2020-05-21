================================
Permissions and authentication
================================

Main attributes
------------------------------------
By default, a mutation is accessible by anything and everyone. To add access-control to a mutation,
the meta-attributes `permissions` and `login_required` is used.


.. code:: python

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            login_required = True
            permissions = ("users.add_user",)


    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            permissions = ("users.change_user", "users.some_custom_perm")


Note that having a permissions *typically*  (but not necessarily) implies that the user is authenticated. Hence
in many cases, simply setting the permissions-array to something is sufficient to guarantee that the user is
authenticated.


The ``get_permissions`` method
------------------------------------
In some scenarios, we might want to grant permission to a mutation conditionally. For this, we can override the
``get_permissions`` classmethod, which by default simply returns the ``permissions``-iterable.

Say for example, we want to grant access to update a user-object if the calling user is the same as the updated user,
or if the calling user has the ``users.change_user``-permission:


.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            login_required = True
            permissions = ("users.change_user",)

        @classmethod
        def get_permissions(cls, root, info, input, id) -> Iterable[str]:
            # Use the disambiguate_id utility from graphene_django_cud to parse the id
            if int(disambiguate_id(id)) == info.context.user.id:
                # Returning an empty array is essentially the same as granting access here.
                return []
            return cls._meta.permissions


The ``get_permissions`` method takes slightly different arguments depending on what mutation is being used.
For patch and update mutations, the method is given ``(root, info, input, id)``. For create mutations,
the method is given ``(root, info, input)``.


Overriding the permissions pipeline
------------------------------------
Internally, all mutations call a method called ``check_permissions`` when checking permissions. The default
implementation of this method simply calls the ``get_permissions``-method, and checks these permissions against
the calling user.

``check_permissions`` will by default raise an exception if the calling user does not have the required permissions.

If some other pipeline is desired for checking permissions, you can override the ``check_permissions``-method.
For instance, we *could* implement the permissions-checking above in the following manner:

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            login_required = True

        @classmethod
        def check_permissions(cls, root, info, input, id):
            if int(disambiguate_id(id)) == info.context.user.id \
               or info.context.user.has_perm("users.change_user"):
                # Not raising an Exception means the calling user has permission to access the mutation
                return

            raise GraphQLError("You do not have permission to access this mutation.")

You can also wrap ``check_permissions`` in decorators, if you so desire.

The ``check_permissions`` method takes slightly different arguments depending on what mutation is being used.
For patch and update mutations, the method is given ``(root, info, input, id)``. For create mutations,
the method is given ``(root, info, input)``.


Wrapping the mutate method
------------------------------------
If none of the above is sufficient, the final frontier is overriding the ``mutate``-method of each mutation class.
Note that that ``check_permissions`` takes essentially the same arguments as ``mutate``. Hence overriding ``mutate``
should only be required in very fringe scenarios.

.. code:: python

    class UpdateUserMutation(DjangoUpdateMutation):
        class Meta:
            model = User
            login_required = True

        @classmethod
        def mutate(cls, root, info, input, id):
            if int(disambiguate_id(id)) != info.context.user.id \
               and not info.context.user.has_perm("users.change_user"):
                raise GraphQLError("You do not have permission to access this mutation.")

            return super().mutate(root, info, input, id)
