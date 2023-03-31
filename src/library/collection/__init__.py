from typing import Any, Dict, Iterator

from src.library.at import AT
from src.library.collection.base_objects import PublisherEnum
from src.library.de import DE
from src.library.us import US


class CollectionMeta(type):
    @property
    def _members(cls) -> Dict[str, Any]:
        return {name: obj for name, obj in cls.__dict__.items() if "__" not in name}

    def __contains__(cls, __x: object) -> bool:
        return __x in cls._members.values()

    def __iter__(cls) -> Iterator[PublisherEnum]:
        for coll in cls._members.values():
            yield from coll

    def __len__(cls) -> int:
        return len(cls._members)


class PublisherCollection(metaclass=CollectionMeta):
    de = DE
    at = AT
    us = US
