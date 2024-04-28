from fundus.publishers.at import AT
from fundus.publishers.base_objects import PublisherCollectionMeta
from fundus.publishers.ch import CH
from fundus.publishers.de import DE
from fundus.publishers.fr import FR
from fundus.publishers.lt import LT
from fundus.publishers.na import NA
from fundus.publishers.tr import TR
from fundus.publishers.uk import UK
from fundus.publishers.us import US


class PublisherCollection(metaclass=PublisherCollectionMeta):
    na = NA
    de = DE
    at = AT
    us = US
    uk = UK
    fr = FR
    ch = CH
    lt = LT
    tr = TR
