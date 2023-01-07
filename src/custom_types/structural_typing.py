from typing import Protocol, runtime_checkable, Union

from src.custom_types.generics import KT, T, VT_co


@runtime_checkable
class HasGet(Protocol):
    """
    Structural type for objects which implement a dict like get methode
    """

    def get(self, key: KT, default: Union[VT_co, T]) -> Union[VT_co, T]:
        ...
