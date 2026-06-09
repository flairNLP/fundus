import re
from typing import Any, Callable, Dict, Protocol

from typing_extensions import ParamSpec

P = ParamSpec("P")


def inverse(filter_func: Callable[P, bool]) -> Callable[P, bool]:
    """Returns a filter that evaluates to the logical NOT of `filter_func`."""

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return not filter_func(*args, **kwargs)

    return __call__


def lor(*filters: Callable[P, bool]) -> Callable[P, bool]:
    """Returns a filter that passes when any of `filters` passes (logical OR)."""

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return any(f(*args, **kwargs) for f in filters)

    return __call__


def land(*filters: Callable[P, bool]) -> Callable[P, bool]:
    """Returns a filter that passes only when all of `filters` pass (logical AND)."""

    def __call__(*args: P.args, **kwargs: P.kwargs) -> bool:
        return all(f(*args, **kwargs) for f in filters)

    return __call__


class URLFilter(Protocol):
    """Filter applied before article download. True means filtered out, False means kept."""

    def __call__(self, url: str) -> bool: ...


def regex_filter(regex: str) -> URLFilter:
    """Returns a URLFilter that filters out URLs matching `regex`."""
    pattern = re.compile(regex)

    def url_filter(url: str) -> bool:
        return bool(pattern.search(url))

    return url_filter


class SupportsBool(Protocol):
    """Anything convertible to bool; the return type of an ExtractionFilter call."""

    def __bool__(self) -> bool: ...


class ExtractionFilter(Protocol):
    """Callable protocol for filters applied after article extraction.

    A truthy return value excludes the article; falsy keeps it — intentionally
    inverse to Python's built-in filter().

    Example — exclude articles whose body is shorter than 500 characters::

        def min_body_length(extraction: Dict[str, Any]) -> bool:
            body = extraction.get("body")
            return not body or len(str(body)) < 500
    """

    def __call__(self, extraction: Dict[str, Any]) -> SupportsBool:
        """Evaluate the extraction and return whether it should be filtered out.

        Args:
            extraction: Maps attribute names to their extracted values, as returned
                by a parser. Attributes absent from the article are not present in the dict.

        Returns:
            A truthy value to exclude the article, falsy to keep it.
        """
        ...


class FilterResultWithMissingAttributes:
    """Return value of Requires.__call__. Truthy when one or more attributes are missing or falsy."""

    def __init__(self, *attributes: str) -> None:
        self.missing_attributes = attributes

    def __bool__(self) -> bool:
        return bool(self.missing_attributes)


def _eval_unless_bool(value: Any) -> bool:
    """Booleans always pass; only non-boolean values are evaluated with bool()."""
    if isinstance(value, bool):
        return True
    else:
        return bool(value)


class Requires:
    """Filters extractions based on the presence and truthiness of named attributes.

    When called with an extraction dict, returns a FilterResultWithMissingAttributes
    that is truthy if any required attribute is absent, falsy, or an Exception.
    With no required attributes specified, all keys in the extraction are evaluated.

    By default, boolean attributes are evaluated with bool():

        Requires("free_access")({"free_access": False})  # filtered out

    Set eval_booleans=False to let boolean values pass unconditionally:

        Requires("free_access", eval_booleans=False)({"free_access": False})  # passes

    Args:
        *required_attributes: Attributes that must be present and truthy. If none are
            given, all keys in the extraction are evaluated.
        eval_booleans: If True, boolean values are evaluated with bool(). If False,
            boolean values always pass. Defaults to True.
    """

    def __init__(self, *required_attributes: str, eval_booleans: bool = True) -> None:
        self.required_attributes = set(required_attributes)
        # somehow mypy does not recognize bool as callable :(
        self._eval: Callable[[Any], bool] = bool if eval_booleans else _eval_unless_bool  # type: ignore[assignment]

    def _is_missing(self, value: Any) -> bool:
        """True if value is absent, falsy, or an Exception."""
        return not self._eval(value) or isinstance(value, Exception)

    def __call__(self, extraction: Dict[str, Any]) -> FilterResultWithMissingAttributes:
        """Evaluate the extraction against the required attributes.

        Args:
            extraction: A dictionary mapping attribute names to their extracted values.

        Returns:
            FilterResultWithMissingAttributes that is truthy if any required attribute
            is absent, falsy, or an Exception.
        """
        attributes = self.required_attributes if self.required_attributes else extraction.keys()
        missing_attributes = [attribute for attribute in attributes if self._is_missing(extraction.get(attribute))]
        return FilterResultWithMissingAttributes(*missing_attributes)


class RequiresAll(Requires):
    """Requires all attributes in the extraction to be present and truthy.

    Equivalent to Requires() with no specified attributes, but with eval_booleans=False
    by default so boolean attributes are not counted as missing regardless of their value.

    Args:
        eval_booleans: If True, boolean values are also evaluated. Defaults to False.
    """

    def __init__(self, eval_booleans: bool = False) -> None:
        super().__init__(eval_booleans=eval_booleans)
