import functools


class _CachedAttribute(object):
    """Computes attribute value and caches it in the instance.
    From https://stackoverflow.com/questions/7388258/replace-property-for-perfomance-gain?noredirect=1&lq=1
    Tweaked a bit to be used with a wrapper.
    """

    def __init__(self, method):
        self.method = method

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        object.__setattr__(inst, self.__name__, result)  # type: ignore[attr-defined]
        return result


# This was implemented in order to
def cached_attribute(attribute):
    """Decorate attributes to be cached.

    This works like `cached_property`, but instead of `property` or `cached_property`, the decorated attribute
    can be overwritten.

    Args:
        attribute: The attribute to decorate.

    Returns:
        A wrapped _CachedAttribute instance.

    """

    def wrapper(func):
        return functools.update_wrapper(_CachedAttribute(func), func)

    return wrapper(attribute)
