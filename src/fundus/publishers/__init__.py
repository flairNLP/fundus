import re
from typing import Set

from fundus.publishers.at import AT
from fundus.publishers.au import AU
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.be import BE
from fundus.publishers.ca import CA
from fundus.publishers.ch import CH
from fundus.publishers.cn import CN
from fundus.publishers.cz import CZ
from fundus.publishers.de import DE
from fundus.publishers.dk import DK
from fundus.publishers.es import ES
from fundus.publishers.fr import FR
from fundus.publishers.gl import GL
from fundus.publishers.il import IL
from fundus.publishers.ind import IND
from fundus.publishers.isl import ISL
from fundus.publishers.it import IT
from fundus.publishers.jp import JP
from fundus.publishers.kr import KR
from fundus.publishers.li import LI
from fundus.publishers.ls import LS
from fundus.publishers.lt import LT
from fundus.publishers.lu import LU
from fundus.publishers.mx import MX
from fundus.publishers.my import MY
from fundus.publishers.na import NA
from fundus.publishers.no import NO
from fundus.publishers.pl import PL
from fundus.publishers.pt import PT
from fundus.publishers.py import PY
from fundus.publishers.ru import RU
from fundus.publishers.tr import TR
from fundus.publishers.tw import TW
from fundus.publishers.tz import TZ
from fundus.publishers.uk import UK
from fundus.publishers.us import US
from fundus.publishers.za import ZA

__all__ = ["Publisher", "PublisherGroup"]


class PublisherCollectionMeta(PublisherGroup):
    def __new__(cls, name, bases, attributes):
        publishers: Set[str] = set()
        for attribute, value in attributes.items():
            # skipp dunder attributes
            if re.search(r"^__.*__$", attribute):
                continue
            elif isinstance(value, PublisherGroup):
                new_publishers: Set[str] = {publisher.__name__ for publisher in value}
                if duplicate_publishers := publishers & new_publishers:
                    raise ValueError(
                        f"Publisher(s) {', '.join(duplicate_publishers)!r} " f"already exists in collection {name!r}."
                    )
                publishers.update(new_publishers)
            elif isinstance(value, Publisher):
                if attribute in publishers:
                    raise ValueError(f"Publishers {value.name!r} already exists in collection {name!r}.")
                publishers.add(attribute)
            else:
                raise TypeError(
                    f"Got unexpected type {type(value)} with value {value!r} "
                    f"Only objects of type {Publisher.__name__!r} or {PublisherGroup.__name__!r} "
                    f"are allowed as class attributes"
                )

        return super().__new__(cls, name, bases, attributes)


class PublisherCollection(metaclass=PublisherCollectionMeta):
    at = AT
    au = AU
    be = BE
    ca = CA
    ch = CH
    cn = CN
    cz = CZ
    de = DE
    dk = DK
    es = ES
    fr = FR
    gl = GL
    il = IL
    ind = IND
    isl = ISL
    it = IT
    jp = JP
    kr = KR
    li = LI
    ls = LS
    lt = LT
    lu = LU
    mx = MX
    my = MY
    na = NA
    no = NO
    pl = PL
    pt = PT
    py = PY
    ru = RU
    tr = TR
    tw = TW
    tz = TZ
    uk = UK
    us = US
    za = ZA
