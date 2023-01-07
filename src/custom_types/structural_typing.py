from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class HasGet(Protocol):
    """
    Structural type for objects which implement a dict like get methode
    """

    def get(self) -> Any:
        ...
