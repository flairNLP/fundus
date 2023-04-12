from fundus.publishers.at import AT
from fundus.publishers.base_objects import CollectionMeta, PublisherEnum, PublisherSpec
from fundus.publishers.de import DE
from fundus.publishers.us import US


class PublisherCollection(metaclass=CollectionMeta):
    de = DE
    at = AT
    us = US
