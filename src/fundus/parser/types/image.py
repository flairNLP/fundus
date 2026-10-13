from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import (
    ClassVar,
    List,
    Optional,
    Union,
)

from fundus.utils.serialization import DataclassSerializationMixin
from fundus.utils.url import is_valid_url, strip_query_and_fragment


@total_ordering
@dataclass
class Dimension(DataclassSerializationMixin):
    width: int
    height: int

    def __mul__(self, other: Union[float, int]) -> "Dimension":
        if isinstance(other, int):
            return Dimension(self.width * other, self.height * other)
        elif isinstance(other, float):
            return Dimension(round(self.width * other), round(self.height * other))
        else:
            raise NotImplementedError(
                f"'*' is not defined between {type(self).__name__!r} and {type(other).__name__!r}"
            )

    def __rmul__(self, other: Union[float, int]) -> "Dimension":
        return self.__mul__(other)

    def __repr__(self) -> str:
        return f"{self.width}x{self.height or '...'}"

    def __lt__(self, other: "Dimension") -> bool:
        if isinstance(other, Dimension):
            if self.width != other.width:
                return self.width < other.width
            else:
                return self.height < other.height
        raise NotImplementedError(f"'<' is not defined between {type(self).__name__!r} and {type(other).__name__!r}")

    def __hash__(self) -> int:
        return hash((self.width, self.height))

    @classmethod
    def from_ratio(
        cls,
        width: Optional[float] = None,
        height: Optional[float] = None,
        ratio: Optional[float] = None,
    ) -> Optional["Dimension"]:
        if width and height:
            return cls(round(width), round(height))
        elif width is not None:
            return cls(round(width), round((width / ratio) if ratio else 0))
        elif height is not None:
            return cls(round((height * ratio) if ratio else 0), round(height))
        else:
            return None


@total_ordering
@dataclass
class ImageVersion(DataclassSerializationMixin):
    __FILE_FORMATS__: ClassVar[List[str]] = ["png", "jpg", "jpeg", "webp"]

    url: str
    query_width: Optional[str] = None
    size: Optional[Dimension] = None
    type: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            url_without_query = strip_query_and_fragment(self.url)
            self.type = self._parse_type(url_without_query)

    def _parse_type(self, url: str) -> Optional[str]:
        if (file_format := url.split(".")[-1]) in self.__FILE_FORMATS__:
            if file_format == "jpg":
                file_format = "jpeg"
            return "image/" + file_format
        return None

    def __repr__(self) -> str:
        if self.size is not None:
            meta = f"{self.size!r}"
        elif self.query_width is not None:
            meta = f"min-width: {self.query_width}px"
        else:
            meta = f"{type(self).__name__}"

        return f"{meta}; {self.type}"

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ImageVersion):
            return NotImplemented
        return self.url == other.url

    def __lt__(self, other: "ImageVersion") -> bool:
        if isinstance(other, ImageVersion):
            if self.size and other.size and self.size != other.size:
                return self.size < other.size
            if (self.size is None) != (other.size is None):
                return self.size is None

            if self.query_width and other.query_width and self.query_width != other.query_width:
                return self.query_width < other.query_width
            if (self.query_width is None) != (other.query_width is None):
                return self.query_width is None

            if self.type and other.type and self.type != other.type:
                return self.type < other.type
            if (self.type is None) != (other.type is None):
                return self.type is None

            return self.url < other.url
        raise NotImplementedError(f"'<' is not defined between {type(self).__name__!r} and {type(other).__name__!r}")


class ImageURLError(Exception): ...


@dataclass(frozen=False)
class Image(DataclassSerializationMixin):
    versions: List[ImageVersion]
    is_cover: bool
    description: Optional[str]
    caption: Optional[str]
    authors: List[str]
    position: int

    def __post_init__(self):
        for url in [version.url for version in self.versions]:
            if not is_valid_url(url):
                raise ImageURLError(f"url {url} is not a valid URL")

    @property
    def url(self) -> str:
        return self.versions[-1].url

    def __str__(self) -> str:
        if self.is_cover:
            representation = "Fundus-Article Cover-Image:\n"
        else:
            representation = "Fundus-Article Image:\n"
        representation += (
            f"-URL:\t\t\t {self.url!r}\n"
            f"-Description:\t {self.description!r}\n"
            f"-Caption:\t\t {self.caption!r}\n"
            f"-Authors:\t\t {self.authors}\n"
            f"-Versions:\t\t {sorted(set(v.size for v in self.versions if v.size is not None))}\n"
        )
        return representation

    def __repr__(self) -> str:
        return self.url
