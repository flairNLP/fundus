import re
from typing import Callable, Dict, Literal, Optional, Pattern, TypeVar, Union, overload

_T = TypeVar("_T")


@overload
def _get_match_dict(pattern: Pattern[str], string: str, conversion: Callable[[str], _T]) -> Dict[str, _T]:
    ...


@overload
def _get_match_dict(
    pattern: Pattern[str], string: str, conversion: Callable[[str], _T], keep_none: Literal[True]
) -> Dict[str, Optional[_T]]:
    ...


@overload
def _get_match_dict(pattern: Pattern[str], string: str) -> Dict[str, str]:
    ...


@overload
def _get_match_dict(pattern: Pattern[str], string: str, keep_none: Literal[True]) -> Dict[str, Optional[str]]:
    ...


def _get_match_dict(  # type: ignore[misc]
    pattern: Pattern[str], string: str, conversion: Optional[Callable[[str], _T]] = None, keep_none: bool = False
) -> Dict[str, Union[str, _T, None]]:
    matches = {}
    for match in re.finditer(pattern, string):
        match_dict = match.groupdict()
        for key, value in match_dict.items():
            if value is not None:
                matches[key] = conversion(value) if conversion is not None else value
            elif keep_none:
                matches[key] = match[key] or value
    return matches
