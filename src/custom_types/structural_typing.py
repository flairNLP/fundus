from typing import Protocol, Any


class HasGet(Protocol):
    """
    Structural type for objects which implement a dict like get methode
    """

    def get(self) -> Any:
        ...
