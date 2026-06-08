import datetime
from typing import Any

import pytest

from fundus.utils.serialization import Serializable, serialize_value


class _SerializableStub:
    def __init__(self, value: Any) -> None:
        self._value = value

    def serialize(self) -> Any:
        return self._value


class TestSerializableProtocol:
    def test_detects_objects_with_serialize_method(self):
        assert isinstance(_SerializableStub("x"), Serializable)

    def test_rejects_objects_without_serialize_method(self):
        assert not isinstance(object(), Serializable)


class TestSerializeValue:
    def test_passes_primitives_through(self):
        assert serialize_value("s") == "s"
        assert serialize_value(42) == 42
        assert serialize_value(3.14) == 3.14
        assert serialize_value(True) is True
        assert serialize_value(None) is None

    def test_serializes_datetime_as_isoformat(self):
        when = datetime.datetime(2024, 1, 2, 3, 4, 5)
        assert serialize_value(when) == "2024-01-02T03:04:05"

    def test_serializes_object_with_serialize_method(self):
        assert serialize_value(_SerializableStub({"k": "v"})) == {"k": "v"}

    def test_walks_lists_recursively(self):
        assert serialize_value([_SerializableStub("a"), _SerializableStub("b")]) == ["a", "b"]

    def test_walks_dicts_recursively(self):
        assert serialize_value({"k": _SerializableStub("v")}) == {"k": "v"}

    def test_normalizes_tuples_to_lists(self):
        assert serialize_value((1, 2, 3)) == [1, 2, 3]

    def test_raises_type_error_on_unserializable(self):
        with pytest.raises(TypeError):
            serialize_value(object())

    def test_error_message_includes_field_name_when_given(self):
        with pytest.raises(TypeError, match="field 'foo'"):
            serialize_value(object(), field_name="foo")
