from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import (
    Dict,
    Iterable,
    List,
    Optional,
    Pattern,
    Set,
    Union,
    cast,
)

import lxml.html
import more_itertools
from dateutil import parser
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.extraction.text import (
    apply_result_filter,
    apply_substitution_pattern_over_list,
    normalize_whitespace,
)
from fundus.utils.serialization import JSONVal

logger = create_logger(__name__)


_json_pattern = re.compile(r"(?P<json>{[\s\S]*}|\[\s*{[\s\S]*}\s*](?!\s*}))")
_json_undefined = re.compile(r'(?P<key>"[^"]*?"):\s*undefined')


def sanitize_json(text: str) -> Optional[str]:
    # capture only content enclosed as follows: {...} or [{...}]
    match = re.search(_json_pattern, text)
    if match is None or not (sanitized := match.group("json")):
        return None

    # substitute "bad" values
    sanitized = re.sub(_json_undefined, r"\g<key>:null", sanitized)
    sanitized = re.sub(r"[\r\n\t]+", "", sanitized)
    return sanitized


def unescape_json_values(obj):
    if isinstance(obj, str):
        return html.unescape(obj)
    elif isinstance(obj, list):
        return [unescape_json_values(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: unescape_json_values(value) for key, value in obj.items()}
    else:
        return obj


def parse_json(text: str) -> Optional[Dict[str, JSONVal]]:
    if not (json_content := sanitize_json(text)):
        return None

    try:
        parsed_json = json.loads(json_content)
        return cast(Dict[str, JSONVal], unescape_json_values(parsed_json))
    except json.JSONDecodeError as error:
        logger.debug(f"Encountered {error!r} during JSON parsing")
        return None


def extract_json_from_dom(root: lxml.html.HtmlElement, selector: XPath) -> Iterable[Dict[str, JSONVal]]:
    jsons = [parsed_json for node in selector(root) if (parsed_json := parse_json(node.text_content())) is not None]
    return more_itertools.collapse(jsons, base_type=dict)


def generic_author_parsing(
    value: Union[
        Optional[str],
        Dict[str, str],
        List[str],
        List[Dict[str, str]],
    ],
    split_on: Optional[List[str]] = None,
    normalize: bool = True,
    substitution_pattern: Optional[Pattern[str]] = None,
    result_filter: Optional[Union[Pattern[str], Set[str]]] = None,
) -> List[str]:
    """This function tries to parse the given <value> to a list of authors (List[str]) based on the type of value.

    Parses based on type of <value> as following:
        value (None):       Empty list \n
        value (str):        re.split(delimiters) with delimiters := split_on or common delimiters' \n
        value (dict):       If key "name" in dict, [dict["name"]] else empty list \n
        value (list[str]):  value\n
        value (list[dict]): [dict["name"] for dict in list if dict["name"]] \n

    with common delimiters := [",", ";", " und ", " and ", " & ", " | "]

    If a result filter is provided, authors matching the pattern or included in the set will be removed.
    If a substitution pattern is provided, any substring matching that pattern will be removed from each author name.

    All values are stripped with default strip() method before returned.

    Args:
        value: An input value representing author(s) which get parsed based on type.
        split_on: Only relevant for type(<value>) = str. If set, split <value> on <split_on>,
            else (default) split <value> on common delimiters.
        normalize: If True, normalize every author with normalize_whitespace(). Defaults to True
        substitution_pattern: If specified, partial matches are removed from each author
        result_filter: Can be of type Pattern[str] or Set[str]. If specified, all authors matching the pattern or
            contained in the set will be removed. Defaults to None.

    Returns:
        A parsed and striped list of authors
    """

    common_delimiters = [",", ";", " und ", " and ", " & ", r" \| "]

    parameter_type_error: TypeError = TypeError(
        f"<value> '{value}' has an unsupported type {type(value)}. "
        f"Supported types are 'Optional[str], Dict[str, str], List[str], List[Dict[str, str]],'"
    )

    def parse_author_dict(author_dict: Dict[str, str]) -> Optional[str]:
        if (author_name := author_dict.get("name")) is not None:
            return author_name

        given_name = author_dict.get("givenName", "")
        additional_name = author_dict.get("additionalName", "")
        family_name = author_dict.get("familyName", "")
        if given_name and family_name:
            return " ".join(filter(bool, [given_name, additional_name, family_name]))
        else:
            return None

    if not value:
        return []

    # collapse
    authors: List[str] = []

    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, str):
            authors.append(item)

        elif isinstance(item, dict):
            if (author := parse_author_dict(item)) is not None:
                authors.append(author)

        else:
            raise parameter_type_error

    if normalize or split_on:

        def split(text: str) -> Iterable[str]:
            return filter(bool, re.split(r"|".join(split_on or common_delimiters), text))

        authors = list(more_itertools.flatten([split(author) for author in authors]))
        normalized_authors = [normalize_whitespace(author) for author in authors if author.strip()]
        authors = normalized_authors
    if substitution_pattern:
        authors = apply_substitution_pattern_over_list(authors, substitution_pattern)
    return apply_result_filter(authors, result_filter)


def generic_topic_parsing(
    keywords: Optional[Union[str, List[str]]],
    delimiter: Union[str, List[str]] = ",",
    substitution_pattern: Optional[Pattern[str]] = None,
    result_filter: Optional[Union[Pattern[str], Set[str]]] = None,
) -> List[str]:
    """This function tries to parse the given <value> to a list of topics (List[str]) based on the type of value.

    Parses based on type of <value> as following:
        value (None):       Empty list \n
        value (str):        re.split(delimiters) with delimiters := delimiter or ',' \n
        value (list[str]):  value\n

    If a result filter is provided, topics matching the pattern or included in the set will be removed.
    If a substitution pattern is provided, any substring matching that pattern will be removed from each topic.

    All values are stripped with default strip() method before returned.

    Args:
        keywords: An input value representing author(s) which get parsed based on type.
        delimiter: Only relevant for type(<value>) = str. If set, split <value> on <delimiter>,
            else (default) split <value> on ','.
        substitution_pattern: If specified, partial matches are removed from each topic
        result_filter: Can be of type Pattern[str] or Set[str]. If specified, all topics matching the pattern or
            contained in the set will be removed. Defaults to None.

    Returns:
        A parsed and striped list of topics
    """
    if isinstance(delimiter, str):
        delimiter = [delimiter]

    if not keywords:
        topics = []
    elif isinstance(keywords, str):
        topics = [
            cleaned
            for keyword in re.split(pattern=f"[{''.join(delimiter)}]", string=keywords)
            if (cleaned := keyword.strip())
        ]
    elif isinstance(keywords, list) and all(isinstance(s, str) for s in keywords):
        topics = keywords
    else:
        raise TypeError(f"Encountered unexpected type {type(keywords)} as keyword parameter")
    if substitution_pattern:
        topics = apply_substitution_pattern_over_list(topics, substitution_pattern)
    return apply_result_filter(topics, result_filter=result_filter)


_tz_infos = {"CET": 3600, "CEST": 7200, "IST": 19800}


class CustomParserInfo(parser.parserinfo):
    MONTHS = [
        ("Jan", "January", "Januar"),
        ("Feb", "February", "Februar"),
        ("Mar", "March", "März"),
        ("Apr", "April"),
        ("May", "May", "Mai"),
        ("Jun", "June", "Juni"),
        ("Jul", "July", "Juli"),
        ("Aug", "August"),
        ("Sep", "Sept", "September"),
        ("Oct", "October", "Oktober", "Okt"),
        ("Nov", "November"),
        ("Dec", "December", "Dezember", "Dez"),
    ]  # type: ignore[assignment]
    # type ignore due to types-python-dateutil==2.9.0.20251008, see https://github.com/flairNLP/fundus/issues/806


def generic_date_parsing(date_str: Optional[str], tz: Optional[timezone] = None) -> Optional[datetime]:
    if date_str is None:
        return None

    if not (parsed_date := parser.parse(date_str, tzinfos=_tz_infos, parserinfo=CustomParserInfo(), fuzzy=True)):
        return None

    if tz is not None and parsed_date.tzinfo is None:
        parsed_date.replace(tzinfo=tz)

    return parsed_date
