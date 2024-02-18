import re
from typing import Any, Callable, Dict, Protocol

from typing_extensions import ParamSpec

P = ParamSpec("P")


def inverse(filter_func: Callable[P, bool]) -> Callable[P, bool]:
    """Logical not operator that can be used on filters

    Args:
        filter_func: The filter function to inverse.

    Returns:
        bool: boolean value of the evaluation
    """

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return not filter_func(*args, **kwargs)

    return __call__


def lor(*filters: Callable[P, bool]) -> Callable[P, bool]:
    """Logical or operator that can be used on filters

    Args:
        *filters: The filter functions to or.

    Returns:
        bool: boolean value of the evaluation
    """

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return any(f(*args, **kwargs) for f in filters)

    return __call__


def land(*filters: Callable[P, bool]) -> Callable[P, bool]:
    """Logical and operator that can be used on filters

    Args:
        *filters: The filter functions to and.

    Returns:
        bool: boolean value of the evaluation
    """

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return all(f(*args, **kwargs) for f in filters)

    return __call__


class URLFilter(Protocol):
    """Protocol to define filter used before article download.

    Filters satisfying this protocol should work inverse to build in filter(),
    so that True gets filtered and False don't.
    """

    def __call__(self, url: str) -> bool:
        """Filters a website, represented by a given <url>, on the criterion if it represents an <article>

        Args:
            url: The url the evaluation should be based on.

        Returns:
            bool: True if an <url> should be filtered out and not
                considered for extraction, False otherwise.

        """
        ...


def regex_filter(regex: str) -> URLFilter:
    def url_filter(url: str) -> bool:
        return bool(re.search(regex, url))

    return url_filter


class SupportsBool(Protocol):
    def __bool__(self) -> bool:
        ...


class ExtractionFilter(Protocol):
    """Protocol to define filters used after article extraction.

    Filters satisfying this protocol should work inverse to build in filter(),
    so that True gets filtered and False don't.
    """

    def __call__(self, extraction: Dict[str, Any]) -> SupportsBool:
        """This should implement a selection based on <extracted>.

        Extracted will be a dictionary returned by a parser mapping the attribute
        names of the parser to the extracted values.

        Args:
            extraction: The extracted values the evaluation
                should be based on.

        Returns:
            bool: True if extraction should be filtered out, False otherwise.

        """
        ...


class FilterResultWithMissingAttributes:
    def __init__(self, *attributes: str) -> None:
        self.missing_attributes = attributes

    def __bool__(self) -> bool:
        return bool(self.missing_attributes)


class Requires:
    def __init__(self, *required_attributes: str) -> None:
        """Class to filter extractions based on attribute values

        If a required_attribute is not present in the extracted data, this filter won't
        be passed.

        Args:
            *required_attributes: Attributes required to evaluate to True in order to
                pass the filter. If no attributes are given, all attributes will be evaluated:
        """
        self.required_attributes = set(required_attributes)

    def __call__(self, extraction: Dict[str, Any]) -> FilterResultWithMissingAttributes:
        missing_attributes = [
            attribute
            for attribute in self.required_attributes or extraction.keys()
            if not bool(value := extraction.get(attribute)) or isinstance(value, Exception)
        ]
        return FilterResultWithMissingAttributes(*missing_attributes)


class RequiresAll(Requires):
    def __init__(self):
        """Name wrap for Requires()

        This is for readability only. It requires all attributes of the extraction to evaluate to True.
        See class:Requires docstring for more information.
        """
        super().__init__()
