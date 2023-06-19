"""Store and read context information globally.

This modul provides functionality to store context information
about different processes in this library. It is mainly used
for debugging/development purposes.
"""

import json
from typing import Any, Dict, TypeVar, Optional

from typing_extensions import Self

_KT = TypeVar("_KT")
_VT_co = TypeVar("_VT_co", covariant=True)


class NestedDict(Dict[Any, Any]):
    def __getitem__(self, __k: _KT) -> Any:
        if not self.get(__k):
            super().__setitem__(__k, {})
        return super().__getitem__(__k)


class Context(NestedDict):
    def __init__(self, name: str):
        global _current_context
        super().__init__()
        if _current_context is None:
            _current_context = self
        else:
            _current_context.update({name: self})
        self._previous_context: Optional[Context] = _current_context
        self.name = name

    def set_active(self):
        global _current_context
        self._previous_context = _current_context
        _current_context = self

    def release(self):
        global _current_context
        _current_context = self._previous_context

    def __str__(self) -> str:
        return json.dumps(self, indent=2, ensure_ascii=False)

    def __enter__(self) -> Self:
        self.set_active()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


_current_context: Optional[Context] = None
global_context = Context("global")
global_context.set_active()


def create_context(name: str) -> Context:
    if _current_context and (context := _current_context.get(name)):
        if isinstance(context, Context):
            return context
        raise ValueError(
            f"There is already a value with name '{name} present within the current "
            f"context '{_current_context.name}' which is not of type {Context}"
        )
    return Context(name)


def get_current_context() -> Context:
    assert _current_context is not None
    return _current_context
