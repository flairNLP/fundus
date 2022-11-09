from typing import Iterator, Any

from src.library.de_de import DE_DE


class CollectionMeta(type):

    @property
    def _members(cls) -> dict[str, Any]:
        return {name: obj for name, obj in cls.__dict__.items() if '__' not in name}

    def __contains__(cls, __x: object) -> bool:
        return __x in cls._members.values()

    def __iter__(cls) -> Iterator:
        return iter(cls._members.values())

    def __len__(cls) -> int:
        return len(cls._members)


class PublisherCollection(metaclass=CollectionMeta):
    de_de = DE_DE
