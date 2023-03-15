from typing import Any, Collection, List, Mapping


def listify(obj: Any) -> List[Any]:
    if isinstance(obj, Mapping):
        return [obj]
    elif isinstance(obj, Collection):
        return list(obj)
    else:
        return [obj]
