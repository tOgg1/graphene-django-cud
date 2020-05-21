# Changelog

## Version 0.6.0
* Renamed DjangoBatchDeleteMutation to DjangoFilterDeleteMutation.
* Added a new DjangoBatchDeleteMutation which takes an array of IDs to delete.
* Added local versions of all overrideable methods. This makes type hinting more accurate.
* Changed the argument order of some of the overrideable methods.
* In particular: Changed the method signature of "get_queryset".

## Version 0.5.3
* Change some potential issue with OneToOne persistence

## Version 0.5.2
* Remove unnecessary debug print.

## Version 0.5.1
* Improve many to many and one to one detection.

## Version 0.5.0
* Add one to one extras handling, allowing for nested functionality for one to one fields.
* Restructure project slightly, by moving mutations to separate files.
* Remove some unnecessary utility functions.

## Version 0.4.4
* Fix bug where default field handling for many-to-many and many-to-one fields failed.

## Version 0.4.3
* Add missing files

## Version 0.4.2
* Update bad handling of AutoFields

## Version 0.4.1
* Ensure AutoFields are disambiguated.

## Version 0.4.0
* Add proper handling of update nested many-to-on extras for update mutations.
* Fix a deprecation warning. See #12. Thanks to @fkromer.

## Version 0.3.2
* Fix bug when converting OneToOneRels.

## Version 0.3.1
* Fix bug in `TimeDelta`

## Version 0.3.0
* `get_queryset` now takes an `info` argument and other kwargs.

## Version 0.2.2
* Fix a bug related to setting of many-to-one extras on create operations.

## Version 0.2.1
* Add better handling of choices fields. Fixes #5.
* Fix handling of "exact" m2m and m2o extras.
* Improve m2o handling of exact and remove extras.

## Version 0.2.0
* Add the `field_types` meta-field, which allows users to override converted field types.

## Version 0.1.0
* Improve test environment
* Add `check_permissions` and `get_permissions` methods. The methods can be overridden to provide custom permissions handling.
* Fix issue with `required`-handling for fields with choices.
* Add queryset handling to delete mutations.
* Add field validation.
* Add `before_mutate`, `before_save` and `after_mutate` hooks.

## Version 0.0.16
* Fix bug related to conversion of filter fields.

## Version 0.0.15
* Fix bug with many to many extras type extraction

## Version 0.0.14
* Loosen graphene-django required version

## Version 0.0.13
* Change package mangement to poetry
* Add missing install dependencies in setup.py
* Move repo to github

## Version 0.0.12
* Fix issue with fields havng name "input": Change items call to use super.

## Version 0.0.11
* Make sure enum fields are fetched from registry

## Version 0.0.10
* Add better handling of filter fields in DjangoBatchDeleteMutation

## Version 0.0.9
* Add DjangoBatchCreateMutation

## Version 0.0.8
* Fix bug with bad auto context field

## Version 0.0.7
* Improve conversion of Boolean field

## Version 0.0.6
* Add customizible names for many to many and many to one rels.

## Version 0.0.5
* Fix some issues with adding/removing many to one rels

## Version 0.0.4
* Fix bug where argument was not sent into update_obj

## Version 0.0.3
* Improve nested auto field name generation

## Version 0.0.2

* Add foreign key, many to many and many to one extras generation.

## Version 0.0.1

Initial release, add core and classes:
 * DjangoCreateMutation
 * DjangoPatchMutation
 * DjangoUpdateMutation
 * DjangoDeleteMutation
 * DjangoBatchDeleteMutation
 
