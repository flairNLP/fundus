import re
from typing import Any, Callable, Dict, Protocol

from typing_extensions import ParamSpec

P = ParamSpec("P")


def inverse(filter_func: Callable[P, bool]) -> Callable[P, bool]:
    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return not filter_func(*args, **kwargs)

    return __call__


class URLFilter(Protocol):
    """Protocol to define filter used before article download.

    Filters satisfying this protocol should work inverse to build in filter(),
    so that True gets filtered and False don't.
    """

    def __call__(self, url: str) -> bool:
        """Filters a website, represented by a given <url>, on the criterion if it represents an <article>

        Args:
            url (str): The url the evaluation should be based on.

        Returns:
            bool: True if an <url> should be filtered out and not
                considered for extraction, False otherwise.

        """
        ...


def regex_filter(regex: str) -> URLFilter:
    def url_filter(url: str) -> bool:
        return bool(re.search(regex, url))

    return url_filter


class ExtractionFilter(Protocol):
    """Protocol to define filters used after article extraction.

    Filters satisfying this protocol should work inverse to build in filter(),
    so that True gets filtered and False don't.
    """

    def __call__(self, extracted: Dict[str, Any]) -> bool:
        """This should implement a selection based on <extracted>.

        Args:
            extracted (dict[str, Any]): The extracted values the evaluation
                should be based on.

        Returns:
            bool: True if extraction should be filtered out, False otherwise.

        """
        ...


class Requires:
    def __init__(self, *required_attributes: str) -> None:
        self.required_attributes = set(required_attributes)

    def __call__(self, extracted: Dict[str, Any]) -> bool:
        return not all(
            bool(value := extracted.get(attr)) and not isinstance(value, Exception) for attr in self.required_attributes
        )
