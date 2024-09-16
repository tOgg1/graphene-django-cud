def get_any_of(dict_or_obj_like, keys, default=None):
    """Get the first key in a dict-like object that is not None"""

    is_dict = isinstance(dict_or_obj_like, dict)

    for key in keys:
        value = dict_or_obj_like.get(key) if is_dict else getattr(dict_or_obj_like, key, None)

        if value is not None:
            return value

    return default
