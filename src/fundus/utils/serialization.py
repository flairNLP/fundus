import json
from typing import Any, Callable, Dict, Sequence, TypeVar, Union

from typing_extensions import TypeAlias

JSONVal: TypeAlias = Union[None, bool, str, float, int, Sequence["JSONVal"], Dict[str, "JSONVal"]]

_T = TypeVar("_T")


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def replace_keys_in_nested_dict(data: Dict[str, _T], transformation: Callable[[str], str]) -> Dict[str, _T]:
    """Recursively replace all keys in a nested dictionary with <transformation>.

    Args:
        data: The dictionary to transform
        transformation: The transformation to use

    Returns:
        The transformed dictionary
    """

    def process(element) -> Any:
        if isinstance(element, dict):
            # Apply transformation to keys and recurse into values
            return {transformation(k): process(v) for k, v in element.items()}
        elif isinstance(element, list):
            # Recursively apply to elements in a list
            return [process(i) for i in element]
        else:
            # Base case: return the value as is if it's not a dict or list
            return element

    return {transformation(k): process(v) for k, v in data.items()}
