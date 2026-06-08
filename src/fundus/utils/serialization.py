import inspect
import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

from typing_extensions import TypeAlias

_T = TypeVar("_T")
_M = TypeVar("_M", bound="DataclassSerializationMixin")
JSONVal: TypeAlias = Union[None, bool, str, float, int, Sequence["JSONVal"], Dict[str, "JSONVal"]]


@runtime_checkable
class Serializable(Protocol):
    """Anything that knows how to convert itself into a JSON-compatible structure.

    Implementing types opt into the export path used by Article.to_json.
    """

    def serialize(self) -> JSONVal: ...


def serialize_value(value: Any, field_name: Optional[str] = None) -> JSONVal:
    """Recursively convert a value to JSON-compatible form.

    Args:
        value: The value to serialize.
        field_name: Optional originating field name, used only for error messages.

    Returns:
        A JSON-serializable structure.

    Raises:
        TypeError: If the value's type has no defined serialization.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [serialize_value(item, field_name) for item in value]
    if isinstance(value, dict):
        return {str(k): serialize_value(v, field_name) for k, v in value.items()}
    if isinstance(value, Serializable):
        return value.serialize()
    location = f"field {field_name!r}" if field_name else "value"
    raise TypeError(f"Cannot serialize {location} of type {type(value).__name__}")


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


class DataclassSerializationMixin:
    def serialize(self) -> Dict[str, JSONVal]:
        if not is_dataclass(self):
            raise TypeError(f"{type(self).__name__!r} is not a dataclass")
        return asdict(self)  # type: ignore[arg-type]

    @classmethod
    def deserialize(cls: Type[_M], serialized: Dict[str, JSONVal]) -> _M:
        if not is_dataclass(cls):
            raise TypeError(f"{type(cls).__name__!r} is not a dataclass")

        # we use get_type_hints here to resolve forward references since we need the actual types
        # not the forwarded string reference
        annotations = get_type_hints(cls)

        for field in fields(cls):
            serialized[field.name] = _inner_deserialize(serialized[field.name], annotations[field.name])

        return cls(**serialized)  # type: ignore[return-value]


def _inner_deserialize(data, cls):
    if data is None:
        return None

    if inspect.isclass(cls) and issubclass(cls, DataclassSerializationMixin):
        return cls.deserialize(data)
    elif (origin := get_origin(cls)) is list:
        item_type = get_args(cls)[0]  # Assuming homogeneous lists
        return [_inner_deserialize(item, item_type) for item in data]
    elif origin is dict:
        key_type, value_type = cls.__args__
        return {_inner_deserialize(k, key_type): _inner_deserialize(v, value_type) for k, v in data.items()}
    elif origin is Union:
        for union_type in cls.__args__:
            if union_type is not None:
                try:
                    return _inner_deserialize(data, union_type)
                except TypeError:
                    continue
        return None
    else:
        return data
