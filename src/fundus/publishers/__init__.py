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
from fundus.publishers.ind import IND
from fundus.publishers.isl import ISL
from fundus.publishers.it import IT
from fundus.publishers.jp import JP
from fundus.publishers.lt import LT
from fundus.publishers.my import MY
from fundus.publishers.na import NA
from fundus.publishers.no import NO
from fundus.publishers.pl import PL
from fundus.publishers.pt import PT
from fundus.publishers.py import PY
from fundus.publishers.tr import TR
from fundus.publishers.tw import TW
from fundus.publishers.tz import TZ
from fundus.publishers.uk import UK
from fundus.publishers.us import US

__all__ = ["Publisher", "PublisherGroup"]

from fundus.publishers.za import ZA


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
    na = NA
    de = DE
    at = AT
    au = AU
    us = US
    uk = UK
    fr = FR
    isl = ISL
    gl = GL
    ch = CH
    lt = LT
    cn = CN
    cz = CZ
    be = BE
    tr = TR
    my = MY
    pt = PT
    pl = PL
    py = PY
    ind = IND
    no = NO
    ca = CA
    es = ES
    jp = JP
    it = IT
    tw = TW
    tz = TZ
    dk = DK
    za = ZA
