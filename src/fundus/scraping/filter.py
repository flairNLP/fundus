import re
from typing import Callable, Protocol


def regex_filter(regex: str) -> Callable[[str], bool]:
    def url_filter(url: str):
        return bool(re.search(regex, url))

    return url_filter


class UrlFilter(Protocol):
    """Filters a website, represented by a given <url>, on the criterion if it represents an <article>.

    <True>:     The <url> is considered to point to an article
    <False>:    The <url> is not considered to point to an article
    """

    def __call__(
        self,
        url: str,
    ) -> bool:
        ...
