# Graphene Django CUD

This package contains a number of helper mutations making it easy to construct create, update and delete mutations for django models.

The helper mutations are:
 * `DjangoCreateMutation`
 * `DjangoBatchCreateMutation`
 * `DjangoPatchMutation`
 * `DjangoUpdateMutation`
 * `DjangoDeleteMutation`
 * `DjangoBatchDeleteMutation`

The package handles both regular ids and relay ids automatically.

## Basic usage

To use, here illustrated by `DjangoCreateMutation`, simply create a new inherting class.
Suppose we have the following model and Node.

    class User(models.Model):
        name = models.CharField(max_length=255)
        address = models.TextField()
        
    class UserNode(DjangoObjectType):
        class Meta:
            model = User
            interfaces = (Node,)

Then we can create a create mutation with the following schema

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User


    class Mutation(graphene.ObjectType):
        create_user = CreateUserMutation.Field()
        
        
    schema = Schema(mutation=Mutation)


Note that the `UserNode` has to be registered as a field before the mutation is instantiated. This will be configurable in the future.

The input to the mutation is a single variable `input` which is automatically created with the models fields.
An example mutation would then be

    mutation {
        createUser(input: {name: "John Doe", address: "Downing Street 10"}){
            user{
                id
                name
                address
            } 
        }
    }

## Mutations

### DjangoCreateMutation

Will create a new mutation which will create a *new* object of the supplied model.

Mutation input arguments:

| Argument | Type   |
| -------- | ------ |
| input    | Object! |

Meta fields:

| Field                 | Type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| only_fields           | Iterable  | None        | If supplied, only these fields will be added as input variables for the model |
| exclude_fields        | Iterable  | None        | If supplied, these fields will be excluded as input variables for the model.  |
| return_field_name     | String    | None        | The name of the return field within the mutation. The default is the camelCased name of the model |  
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |
| auto_context_fields   | Dict      | None        | A mapping of context values into model fields. See below |
| optional_fields       | Tuple     | ()          | A list of fields which explicitly should have `required=False` |
| required_fields       | Tuple     | None        | A list of fields which explicitly should have `required=True` |
| type_name             | String    | None        | If supplied, the input variable in the mutation will have its typename set to this string. This is useful when creating multiple mutations of the same type for a single model. |
| many_to_many_extras   | Dict      | {}          | A dict with extra information regarding many-to-many fields. See below.  | I        
| many_to_one_extras    | Dict      | {}          | A dict with extra information regarding many-to-one relations. See below.  |
| foreign_key_extras    | Dict      | {}          | A dict with extra information regarding foreign key extras.  |

#### Example mutation

    mutation {
        createUser(input: {name: "John Doe", address: "Downing Street 10"}){
            user{
                id
                name
                address
            } 
        }
    }
    
### DjangoBatchCreateMutation

Will create a new mutation which will create multiple *new* objects of the supplied model.

Mutation input arguments:

| Argument | Type   |
| -------- | ------ |
| input    | [Object]! |

Meta fields:

| Field                 | Type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| only_fields           | Iterable  | None        | If supplied, only these fields will be added as input variables for the model |
| exclude_fields        | Iterable  | None        | If supplied, these fields will be excluded as input variables for the model.  |
| return_field_name     | String    | None        | The name of the return field within the mutation. The default is the camelCased name of the model |  
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |
| auto_context_fields   | Dict      | None        | A mapping of context values into model fields. See below. |
| optional_fields       | Tuple     | ()          | A list of fields which explicitly should have `required=False` |
| required_fields       | Tuple     | None        | A list of fields which explicitly should have `required=True` |
| type_name             | String    | None        | If supplied, the input variable in the mutation will have its typename set to this string. This is useful when creating multiple mutations of the same type for a single model. |
| use_type_name         | String    | None        | If supplied, no new input type will be created, and instead the registry will be queried for an input type with that name. Note that supplying this value will invalidate many other arguments, as they are only relevant for creating the new input type. |
| many_to_many_extras   | Dict      | {}          | A dict with extra information regarding many-to-many fields. See below.  | I        
| many_to_one_extras    | Dict      | {}          | A dict with extra information regarding many-to-one relations. See below.  |
| foreign_key_extras    | Dict      | {}          | A dict with extra information regarding foreign key extras.  |

#### Example mutation

    mutation{
        batchCreateUser(input: [{name: "John Doe", address: "Downing Street 10"}]){
            user{
                id
                name
                address
            } 
        }
    }


### DjangoUpdateMutation

Will update an existing instance of a model. The UpdateMutation (in contrast to the PatchMutation) requires
all fields to be supplied by default.

Mutation input arguments:

| Argument | Type    |
| -------- | ------  |
| id       | ID!     |
| input    | Object! |

All meta arguments:

| Argument              | type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| only_fields           | Iterable  | None        | If supplied, only these fields will be added as input variables for the model |
| exclude_fields        | Iterable  | None        | If supplied, these fields will be excluded as input variables for the model.  |
| return_field_name     | String    | None        | The name of the return field within the mutation. The default is the camelCased name of the model |  
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |
| auto_context_fields   | Dict      | None        | A mapping of context values into model fields. See below |
| optional_fields       | Tuple     | ()          | A list of fields which explicitly should have `required=False` |
| required_fields       | Tuple     | None        | A list of fields which explicitly should have `required=True` |
| type_name             | String    | None        | If supplied, the input variable in the mutation will have its typename set to this string. This is useful when creating multiple mutations of the same type for a single model. |
| many_to_many_extras   | Dict      | {}          | A dict with extra information regarding many-to-many fields. See below.  | I        
| many_to_one_extras    | Dict      | {}          | A dict with extra information regarding many-to-one relations. See below.  |
| foreign_key_extras    | Dict      | {}          | A dict with extra information regarding foreign key extras.  |

#### Example mutation

    mutation {
        updateUser(id: "VXNlck5vZGU6MQ==", input: {
            name: "John Doe", 
            address: "Downing Street 10"
        }){
            user{
                id
                name
                address
            } 
        }
    }


### DjangoPatchMutation

Will update an existing instance of a model. The PatchMutation (in contrast to the UpdateMutation) does not 
require all fields to be supplied. I.e. all are fields are optional.

Mutation input arguments:

| Argument | Type    |
| -------- | ------  |
| id       | ID!     |
| input    | Object! |

All meta arguments:

| Argument              | type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| only_fields           | Iterable  | None        | If supplied, only these fields will be added as input variables for the model |
| exclude_fields        | Iterable  | None        | If supplied, these fields will be excluded as input variables for the model.  |
| return_field_name     | String    | None        | The name of the return field within the mutation. The default is the camelCased name of the model |  
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |
| auto_context_fields   | Dict      | None        | A mapping of context values into model fields. See below |
| optional_fields       | Tuple     | ()          | A list of fields which explicitly should have `required=False` |
| required_fields       | Tuple     | None        | A list of fields which explicitly should have `required=True` |
| type_name             | String    | None        | If supplied, the input variable in the mutation will have its typename set to this string. This is useful when creating multiple mutations of the same type for a single model. |
| many_to_many_extras   | Dict      | {}          | A dict with extra information regarding many-to-many fields. See below.  | I        
| many_to_one_extras    | Dict      | {}          | A dict with extra information regarding many-to-one relations. See below.  |
| foreign_key_extras    | Dict      | {}          | A dict with extra information regarding foreign key extras.  |

#### Example mutation

    mutation {
        updateUser(id: "VXNlck5vZGU6MQ==", input: {
            name: "John Doe", 
        }){
            user{
                id
                name
                address
            } 
        }
    }



### DjangoDeleteMutation

Will delete an existing instance of a model. The returned arguments are:

* `found`: True if the instance was found and deleted.
* `deletedId`: THe id of the deleted instance.

Mutation input arguments:

| Argument | Type    |
| -------- | ------  |
| id       | ID!     |

All meta arguments:

| Argument              | type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |

#### Example mutation

    mutation {
        deleteUser(id: "VXNlck5vZGU6MQ=="){
            found
            deletedId
        }
    }

### DjangoBatchDeleteMutation

Will delete multiple instances of a model depending on supplied filters. The returned arguments are:

* `deletionCount`: True if the instance was found and deleted.
* `deletedIds`: The ids of the deleted instances.

Mutation input arguments:

| Argument | Type    |
| -------- | ------  |
| input    | Object!     |

All meta arguments:

| Argument              | type      | Default     | Description |
| --------              | ---       | ----------- | ----------------------------------------------- |
| model                 | Model     | None        | The model. **Required**.
| filter_fields         | Tuple     | ()          | A number of filter fields which allow us to restrict the instances to be deleted. |
| permissions           | Tuple     | None        | The permissions required to access the mutation |
| login_required        | Boolean   | None        | If true, the calling user has to be authenticated |

If there are multiple filters, these will be combined with **and**-clauses. For or-clauses, use multiple mutation calls. 

#### Example

Class, with an assumed foreign key to a `House` model:
    
    class BatchDeleteUser(DjangoBatchDeleteMutation):
        class Meta:
            model = User
            filter_fields = ('name', 'house__address',)

Mutation:

    mutation {
        batchDeleteUser(input: {name: 'John'}){
            deletedIds
            deletionCount
        }
    }

## Auto context fields

The create, update and patch mutations contains a meta-field `auto_context_fields`. It allows us to automatically assign
field values depending on values in the context (i.e. the current `HttpRequest`). Most typically, this will
be used to automatically assign the the current user to some field.

Suppose for instance you have the following model:

    class ForumThread(models.Model):
        created_by = models.ForeignKey(User, on_delete=models.CASCADE)
        
        # More fields

We can then automatically assign the created_by field to the calling user by creating a mutation:


    class CreateForumThreadMutation(DjangoCreateMutation):
        class Meta:
            auto_context_fields = {
                'created_by': 'user' 
            }
            
            
Presupposing, of course, that the `user`  field of the `info.context` (HttpRequest) field is set. This works with any context field.
Also note that auto context fields are automatically set as `required=False`, to please Graphene. Finally note that
if we add an explicit value to the `createdBy` field when calling the mutation, this value will override the auto context field.

## Extras and nested mutations

There are three meta fields which allow us to extend the handling of both sides of a foreign key relationship (foreign key extras and many to one extras),
 as well as many to many relationships.

### Foreign key extras

The `foreign_key_extras` field is a dictionary containing information regarding how to handle a model's foreign keys. Here is an example:

    class Cat(models.Model):
        owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cats")
        name = models.TextField(

    class CreateCatMutation(DjangoCreateMutation):
        class Meta:
            model = Cat
            foreign_key_extras = {"owner": {"type": "CreateUserInput"}}
            
By default, the `owner` field is of type `ID!`, i.e. you have to supply the ID of an owner when creating a cat.
But suppose you instead for every cat want to create a new user as well. Well that's exactly what this mutation allows for (demands).

Here, the `owner` field will now be of type `CreateUserInput!`, which has to have been created before, typically via a `CreateUserMutation`, which by default will result in the type name `CreateUserInput`.
An example call to the mutation is:

    mutation {
        createCat(input: {owner: {name: "John Doe"}, name: "Kitty"}){
            cat{
                name
                owner {
                    id
                    name
                } 
            }
        }
    }
    
A current TODO here is to allow the type to be `auto`, which will automatically create a new type. This is useful in cases where you don't want to reuse an existing type.

### Many to one extras

The `many_to_one_extras` field is a dictionary containing information regarding how to handle many to one relations, i.e. the "other" side of a
foreign key.  Suppose we have the `Cat` model as above. Looking from the User-side, we could add nested creations of Cat's, by the following mutation


    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            many_to_one_extras = {
                "cats": {
                    "add": {"type": "auto"}
                }
            }
            
This will add an input argument `catsAdd`, which accepts an array of Cat objects. Note that the type value `auto` means that a new type to accept the cat object will be created.
This is usually necessary, as the regular `CreateCatInput` requires an owner id, which we do not want to give here, as it is inferred.

Now we could create a user with multiple cats in one go as follows:

    
    mutation {
        createUser(input: {
            name: "User",
            catsAdd: [
                {name: "First Kitty"},
                {name: "Second kitty"}
            ] 
        }){
            user{
                id
                name
                cats{
                    edges{
                        node{
                            id
                        } 
                    }
                }
            }
        }
    }


Note that the default many to one relation argument `cats` still accepts a list of inputs. You might want to keep it this
way. However, you can override the default by adding an entry with the key "exact":


    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            many_to_one_extras = {
                "cats": {
                    "exact": {"type": "auto"}
                }
            }
    

Note that we can add a new key with the type "ID", to still allow for Cat objects to be added by id.

    
    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            many_to_one_extras = {
                "cats": {
                    "exact": {"type": "auto"},
                    "by_id": {"type": "ID"}
                }
            }

    
    mutation {
        createUser(input: {
            name: "User",
            cats: [
                {name: "First Kitty"},
                {name: "Second kitty"}
            ],
            catsById: ["Q2F0Tm9kZTox"]
        }){
            user{
                ...UserInfo
            }
        }
    }

### Many to many extras

The `many_to_one_extras` field is a dictionary containing information regarding how to handle many to many relations.
Suppose we have the `Cat` model as above, and a `Dog` model like:

    class Dog(models.Model):
        owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
        name = models.TextField()
        
        enemies = models.ManyToManyField(Cat, blank=True, related_name='enemies')
        
        def is_stray():
            return self.owner is None

    
    class DogNode(DjangoObjectType):
        class Meta:
            model = Dog
    
We now have a many to many relationship, which by default will be modelled by default using an `[ID]` argument. However, this can be customized
fairly similar to many to one extras:

    class CreateDogMutation(DjangoCreateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                'enemies': {
                    'add': {"type": "CreateCatInput"} 
                } 
            }
         
This will, similar to before, add an `enemiesAdd` argument:

    mutation {
        createDog(input: {
            name: "Buster", 
            enemies: ["Q2F0Tm9kZTox"], 
            enemiesAdd: [{owner: "VXNlck5vZGU6MQ==", name: "John's cat"]
        }}){
            dog{
                ...DogInfo 
            } 
        }
    }


This will create a dog with two enemies, one that already exists, and a new one, which has the owner `VXNlck5vZGU6MQ==` (some existing user).
Note that if `CreateCatInput` expects us to create a new user, we would have to do that here.

We can also add an extra field here for removing entities from a many to many relationship:

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "add": {"type": "CreateCatInput"},
                    "remove": {"type": "ID"},
                    # A similar form would be "remove": true
                } 
            }
            
Note that this _has_ to have the type "ID". Also note that this has no effect on `DjangoCreateMutation` mutations. 
We could then perform

    mutation {
        updateDog(id: "RG9nTm9kZTox", input: {
            name: "Buster 2", 
            enemiesRemove: ["Q2F0Tm9kZTox"],
            enemiesAdd: [{owner: "VXNlck5vZGU6MQ==", name: "John's cat"]
        }}){
            dog{
                ...DogInfo 
            } 
        }
    }

This would remove "Q2F0Tm9kZTox" as an enemy, but create a new one as before. 

We can alter the behaviour of the default argument (e.g. `enemies`), by adding the "exact":

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "exact": {"type": "CreateCatInput"},
                    "remove": {"type": "ID"},
                    # A similar form would be "remove": true
                } 
            }

    mutation {
        updateDog(id: "RG9nTm9kZTox", input: {
            name: "Buster 2", 
            enemiesRemove: ["Q2F0Tm9kZTox"],
            enemiesAdd: [{owner: "VXNlck5vZGU6MQ==", name: "John's cat"]
        }}){
            dog{
                ...DogInfo 
            } 
        }
    }

This will have the rather odd behavior that all enemies are reset, and only the new ones created will be
added to the relationship. In other words it exists as a sort of `purge and create` functionality.
When used in a `DjangoCreateMutation` it will simply function as an initial populator of the relationship.
            
A TODO here is adding the type `auto` for many to many extras.
        
### Other aliases

In both the many to many and many to one extras cases, the naming of the extra fields are not arbitrary. However, they can
be customized; with effect in particular for many to many extras. Suppose you want your field to be named `enemiesKill`,
which should remove from a many to many relationship. Then initially, we might write:

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "exact": {"type": "CreateCatInput"},
                    "kill": {"type": "ID"},
                } 
            }

Unfortunately, this will not work, as graphene-django-cud does not know what operation `kill` translates to? Should we add or remove (or set) the entities?
Fortunately, we explicit tell which operation to use, by supplying the "operation" key:

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "exact": {"type": "CreateCatInput"},
                    "kill": {"type": "ID", "operation": "remove"},
                } 
            }

Legal values are "add", "remove", and "update" (and some aliases of these). 

If you want even more flexible fields, you can also explicitly set the name:

    class UpdateDogMutation(DjangoUpdateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "exact": {"type": "CreateCatInput"},
                    "additional": {"type": "ID", "operation": "remove", "name": "additional_enemies"},
                } 
            }

Note that the name will be translated from snake_case to camelCase as per usual. Had we not added the name here, it would have
defaulted to "enemiesAdditional", instead of "additionalEnemies".
    
### Deep nested arguments

Note that deeply nested arguments are added by default when using existing types. Hence, for the mutation

    class CreateDogMutation(DjangoCreateMutation):
        class Meta:
            model = Dog
            many_to_many_extras = {
                "enemies": {
                    "exact": {"type": "CreateCatInput"},
                } 
            }
            
Where `CreateCatInput` is the type generated for

    class CreateCatMutation(DjangoCreateMutation):
        class Meta:
            model = Cat
            many_to_many_extras = {
                "targets": {"exact": {"type": "CreateMouseInput"}},
            }
            foreign_key_extras = {"owner": {"type": "CreateUserInput"}}

Where we assume we have now also created a new model `Mouse` with a standard `CreateMouseMutation` mutation. We could then
execute with success the following massive mutation:


    mutation {
        createDog(input: {
            owner: null, 
            name: "Spark",
            enemies: [
                {
                    name: "Kitty", 
                    owner: {name: "John doe"}, 
                    targets: [
                        {name: "Mickey mouse"}
                    ]
                },
                {
                    name: "Kitty",
                    owner: {name: "Ola Nordmann"}
                }
            ]
       }){
            ...DogInfo
       }
    }

This creates a new (stray) dog, two new cats with one new owner each and one new mouse. The new cats
and the new dog are automatically set as enemies, and the mouse is automatically set as a target of the first cat.

For `auto` fields, we can create nested behaviour explicitly:

    class CreateUserMutation(DjangoCreateMutation):
        class Meta:
            model = User
            many_to_one_extras = {
                "cats": {
                    "exact": {
                        "type": "auto",
                        "many_to_many_extras": {
                            "enemies": {
                                "exact": {
                                   "type": "CreateDogInput"
                                }
                            } 
                        }
                    }
                }
            }

There is no limit to how deep this recursion may go, apart from your imagination.


## Handle functions

TODO

## Validate functions

TODO


## get_ functions

TODO

## Examples

TODO

## Limitations and known issues

One could wish for an API where you could specify both IDs and objects in a single array for many to many and many to one relations.
However, due to GraphQLs strict type system, this is not currently possible — in particular due to the fact that scalars and object types cannot be together in a union.

Some workarounds could be implemented for this, but we deem this more dirty than useful.
