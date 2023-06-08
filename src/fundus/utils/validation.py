from typing import Any, Iterable, List, Mapping


def listify(obj: Any) -> List[Any]:
    if isinstance(obj, Mapping):
        return [obj]
    elif isinstance(obj, Iterable):
        return list(obj)
    else:
        return [obj]
