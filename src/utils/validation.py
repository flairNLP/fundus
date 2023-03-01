from typing import Mapping, Collection


def listify(obj: ...) -> list:
    if isinstance(obj, Mapping):
        return [obj]
    elif isinstance(obj, Collection):
        return list(obj)
    else:
        return [obj]
