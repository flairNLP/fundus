from src.fundus.publishers.at import AT
from src.fundus.publishers.base_objects import (
    CollectionMeta,
    PublisherEnum,
    PublisherSpec,
)
from src.fundus.publishers.de import DE
from src.fundus.publishers.us import US


class PublisherCollection(metaclass=CollectionMeta):
    de = DE
    at = AT
    us = US
