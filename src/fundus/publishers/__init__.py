from fundus.publishers.at import AT
from fundus.publishers.base_objects import CollectionMeta, PublisherEnum, PublisherSpec


class PublisherCollection(metaclass=CollectionMeta):
    at = AT
