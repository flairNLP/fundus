import itertools
import json
import re
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from functools import total_ordering
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Match,
    Optional,
    Pattern,
    Type,
    Union,
)
from urllib.parse import urljoin, urlparse

import lxml.html
import more_itertools
import validators
from dateutil import parser
from lxml import etree
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.data import (
    ArticleBody,
    ArticleSection,
    Image,
    LinkedDataMapping,
    TextSequence,
)

logger = create_logger(__name__)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


@total_ordering
@dataclass(eq=False)
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    _break_selector: ClassVar[XPath] = XPath("*//br")

    # one could replace this recursion with XPath using an expression like this:
    # //*[not(self::script) and text()]/text(), but for whatever reason, that's actually 50-150% slower
    # than simply using the implemented mixture below
    def text_content(self, excluded_tags: Optional[List[str]] = None) -> str:
        guarded_excluded_tags: List[str] = excluded_tags or []

        def _text_content(element: lxml.html.HtmlElement) -> str:
            if element.tag in guarded_excluded_tags:
                return ""
            text = element.text or "" if not isinstance(element, lxml.html.HtmlComment) else ""
            children = "".join([_text_content(child) for child in element.iterchildren()])
            tail = element.tail or ""
            return text + children + tail

        return _text_content(self._get_break_preserved_node())

    def _get_break_preserved_node(self) -> lxml.html.HtmlElement:
        copied_node = copy(self.node)
        for br in self._break_selector(copied_node):
            br.tail = "\n" + br.tail if br.tail else "\n"
        return copied_node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.position == other.position

    def __lt__(self, other: "Node") -> bool:
        return self.position < other.position

    def __hash__(self) -> int:
        return hash(self.position)

    def __str__(self) -> str:
        return self.text_content()

    def __repr__(self):
        return f"{type(self).__name__}: {self.text_content()}"

    def __bool__(self):
        return bool(normalize_whitespace(self.text_content()))


class SummaryNode(Node):
    pass


class SubheadNode(Node):
    pass


class ParagraphNode(Node):
    pass


def extract_article_body_with_selector(
    doc: lxml.html.HtmlElement,
    paragraph_selector: XPath,
    summary_selector: Optional[XPath] = None,
    subheadline_selector: Optional[XPath] = None,
) -> ArticleBody:
    # depth first index for each element in tree
    df_idx_by_ref = {element: i for i, element in enumerate(doc.iter())}

    def extract_nodes(selector: XPath, node_type: Type[Node]) -> List[Node]:
        if not selector and node_type:
            raise ValueError("Both a selector and node type are required")

        return [node for element in selector(doc) if (node := node_type(df_idx_by_ref[element], element))]

    summary_nodes = extract_nodes(summary_selector, SummaryNode) if summary_selector else []
    subhead_nodes = extract_nodes(subheadline_selector, SubheadNode) if subheadline_selector else []
    paragraph_nodes = extract_nodes(paragraph_selector, ParagraphNode)
    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    if not nodes:
        # return empty body if no text is present
        return ArticleBody(TextSequence([]), [])

    instructions = more_itertools.split_when(nodes, pred=lambda x, y: type(x) != type(y))

    if not summary_nodes:
        instructions = more_itertools.prepend([], instructions)
    elif not nodes[: len(summary_nodes)] == summary_nodes:
        raise ValueError(f"All summary nodes should be at the beginning of the article")

    if not subhead_nodes or (paragraph_nodes and subhead_nodes[0] > paragraph_nodes[0]):
        first = next(instructions)
        instructions = itertools.chain([first, []], instructions)

    summary = TextSequence(
        map(lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"])), next(instructions))
    )
    sections: List[ArticleSection] = []

    for chunk in more_itertools.chunked(instructions, 2):
        if len(chunk) == 1:
            chunk.append([])
        texts = [list(map(lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"])), c)) for c in chunk]
        sections.append(ArticleSection(*map(TextSequence, texts)))

    return ArticleBody(summary=summary, sections=sections)


_ld_node_selector = XPath("//script[@type='application/ld+json']")
_json_pattern = re.compile(r"(?P<json>{[\s\S]*}|\[\s*{[\s\S]*}\s*](?!\s*}))")


def extract_json_from_dom(root: lxml.html.HtmlElement, selector: XPath) -> Iterable[Dict[str, Any]]:
    def sanitize(text: str) -> Optional[str]:
        # capture only content enclosed as follows: {...} or [{...}]
        match = re.search(_json_pattern, text)
        if match is not None and (sanitized := match.group("json")):
            return sanitized
        return None

    json_nodes = selector(root)
    jsons = []
    for node in json_nodes:
        json_content = sanitize(node.text_content()) or ""
        try:
            jsons.append(json.loads(json_content))
        except json.JSONDecodeError as error:
            logger.debug(f"Encountered {error!r} during JSON parsing")
    return more_itertools.collapse(jsons, base_type=dict)


def get_ld_content(root: lxml.html.HtmlElement) -> LinkedDataMapping:
    """Parse JSON-LD from HTML.

    This function parses a script tags of type ld+json.
    In case the JSON is wrapped in a CDATA tag it is first stripped.

    Args:
        root: The HTML document given as a lxml.html.HtmlElement.

    Returns:
        The JSON-LD data as a LinkedDataMapping
    """

    return LinkedDataMapping(extract_json_from_dom(root, _ld_node_selector))


_meta_node_selector = CSSSelector("head > meta, body > meta")


def get_meta_content(root: lxml.html.HtmlElement) -> Dict[str, str]:
    """Parse metadata from HTML.

    This function parses single values (i.e. charset=...), nodes containing name, property, http-equiv or
    itemprop attributes. When multiple values for the same key occur, they will be joined using `,`. This
    is in order to ease typing and avoid list as additional type.

    In case an HTML tag consists a class, it will be appended as namespace to avoid key collisions.
    I.e. <meta class="swiftype" name="author" ... > will be stored using `swiftype:author` as a key.

    Args:
        root: The HTML document given as a lxml.html.HtmlElement.

    Returns:
        The metadata as a dictionary
    """
    data = defaultdict(list)
    for node in _meta_node_selector(root):
        attributes = node.attrib
        if len(attributes) == 1:
            data[attributes.keys()[0]].append(attributes.values()[0])
        elif key := (  # these keys are ordered by frequency
            attributes.get("name")
            or attributes.get("property")
            or attributes.get("http-equiv")
            or attributes.get("itemprop")
        ):
            if ns := attributes.get("class"):
                key = f"{ns}:{key}"
            if content := attributes.get("content"):
                data[key].append(content)

    metadata: Dict[str, str] = {}
    for name, listed_content in data.items():
        if len(listed_content) == 1:
            metadata[name] = listed_content[0]
        else:
            # for ease of typing we join multiple contents for the same key using ','
            metadata[name] = ",".join(listed_content)

    return metadata


def strip_nodes_to_text(text_nodes: List[lxml.html.HtmlElement], join_on: str = "\n\n") -> Optional[str]:
    if not text_nodes:
        return None
    return join_on.join(([re.sub(r"\n+", " ", node.text_content()) for node in text_nodes])).strip()


def generic_nodes_to_text(nodes: List[lxml.html.HtmlElement], normalize: bool = False) -> List[str]:
    if not nodes:
        return []
    texts = [
        normalize_whitespace(str(node.text_content())) if normalize else str(node.text_content()) for node in nodes
    ]
    return [text for text in texts if text]


def apply_substitution_pattern_over_list(
    input_list: List[str], pattern: Pattern[str], replacement: Union[str, Callable[[Match[str]], str]] = ""
) -> List[str]:
    return [subbed for text in input_list if (subbed := re.sub(pattern, replacement, text).strip())]


def generic_author_parsing(
    value: Union[
        Optional[str],
        Dict[str, str],
        List[str],
        List[Dict[str, str]],
    ],
    split_on: Optional[List[str]] = None,
    normalize: bool = True,
) -> List[str]:
    """This function tries to parse the given <value> to a list of authors (List[str]) based on the type of value.

    Parses based on type of <value> as following:
        value (None):       Empty list \n
        value (str):        re.split(delimiters) with delimiters := split_on or common delimiters' \n
        value (dict):       If key "name" in dict, [dict["name"]] else empty list \n
        value (list[str]):  value\n
        value (list[dict]): [dict["name"] for dict in list if dict["name"]] \n

    with common delimiters := [",", ";", " und ", " and ", " & ", " | "]

    All values are stripped with default strip() method before returned.

    Args:
        value:      An input value representing author(s) which get parsed based on type
        split_on:   Only relevant for type(<value>) = str. If set, split <value> on <split_on>,
            else (default) split <value> on common delimiters

    Returns:
        A parsed and striped list of authors
    """

    common_delimiters = [",", ";", " und ", " and ", " & ", " \| "]

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
        normalized_authors = [normalize_whitespace(author) for author in authors]
        return normalized_authors

    return authors


def generic_text_extraction_with_css(doc, selector: XPath) -> Optional[str]:
    nodes = selector(doc)
    return strip_nodes_to_text(nodes)


def generic_topic_parsing(keywords: Optional[Union[str, List[str]]], delimiter: str = ",") -> List[str]:
    if not keywords:
        return []
    elif isinstance(keywords, str):
        return [cleaned for keyword in keywords.split(delimiter) if (cleaned := keyword.strip())]
    elif isinstance(keywords, list) and all(isinstance(s, str) for s in keywords):
        return keywords
    else:
        raise TypeError(f"Encountered unexpected type {type(keywords)} as keyword parameter")


_tz_infos = {"CET": 3600, "CEST": 7200}


def generic_date_parsing(date_str: Optional[str]) -> Optional[datetime]:
    return parser.parse(date_str, tzinfos=_tz_infos) if date_str else None


_title_selector = CSSSelector("title")


def parse_title_from_root(root: lxml.html.HtmlElement) -> Optional[str]:
    title_node = _title_selector(root)

    if len(title_node) != 1:
        return None

    return strip_nodes_to_text(title_node)


def get_fundus_image_from_dict(json_dict: Dict[str, Any], domain: str) -> Optional[Image]:
    """
    Given a ld_json dictionary of type ImageObject, this helper function tries to parse the image and extract caption,
    description and authors, if possible.
    @param json_dict: Json Dictionary of type ImageObject
    @param domain: Domain of the website hosting the image
    @return: If the URL is valid, an Image object is returned
    """
    if (url := (json_dict.get("url") or json_dict.get("contentUrl"))) and isinstance(url, list):
        valid_urls = list()
        for url_str in url:
            url_str = preprocess_url(url_str, domain)
            if validators.url(url_str):
                valid_urls.append(url_str)
        if valid_urls:
            return Image(
                valid_urls,
                description=json_dict.get("description"),
                caption=json_dict.get("caption"),
                author=generic_author_parsing(json_dict.get("author")),
            )
        return None

    elif url:
        url = preprocess_url(url, domain)
        if validators.url(url):
            return Image(
                [url],
                description=json_dict.get("description"),
                caption=json_dict.get("caption"),
                author=generic_author_parsing(json_dict.get("author")),
            )
    return None


def preprocess_url(url: str, domain: str) -> str:
    url = re.sub(r"\\/", "/", url)
    # Some publishers use relative URLs
    if not validators.url(url):
        publisher_domain = "https://" + (domain if domain.endswith("/") else domain + "/")
        url = urljoin(publisher_domain, url.removeprefix("/"))
    return url


def extract_image_data_from_html(
    doc: lxml.html.HtmlElement,
    input_images: list[Image],
    paragraph_selector: Union[CSSSelector, XPath],
    upper_boundary_selector: Union[CSSSelector, XPath] = XPath("//main"),
    caption_selector: Union[CSSSelector, XPath] = XPath("./ancestor::figure//figcaption"),
    alt_selector: Union[CSSSelector, XPath] = XPath("./@alt"),
    author_selector: Union[CSSSelector, XPath] = XPath(
        "(./ancestor::figure//*[(contains(@class, 'copyright') or contains(@class, 'credit')) and text()])[1]"
    ),
    author_pattern: Optional[Pattern] = None,
) -> List[Image]:
    """
    This function extracts the information related to a given List of Images from the HTML document. Note that this
    function does not verify the existence of an Image in the HTML but rather considers the image object, that has
    the most similar src link.
    @param doc: The HTML document corresponding to the Fundus article containing the images
    @param input_images: List of Fundus Images found in the article.
    @param paragraph_selector: Selector used to select the paragraphs of the article.
    @param upper_boundary_selector: A selector referencing an element to be considered as the upper boundary. All img
    elements before this element will be ignored.
    @param caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element
    @param alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
    @param author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
    figure with copyright or credit in its class attribute.
    @param author_pattern: If the authors are only mentioned in the caption, a regex expression can be used to match the
    authors. A captioning group named 'credits' should be used.
    @return: List with images filtered to be between the specified upper boundary and last paragraph
    """
    filtered_list = list()
    img_selector = XPath("//img")
    img_elements = img_selector(doc)
    img_elements_with_src = list()
    paragraphs = paragraph_selector(doc)
    upper_boundary_elements = upper_boundary_selector(doc)
    if not paragraphs or not img_elements:
        return []
    first_paragraph = paragraphs[0]
    last_paragraph = paragraphs[-1]
    upper_boundary = None
    if upper_boundary_elements:
        upper_boundary = upper_boundary_elements[0]
    for img_element in img_elements:
        if (img_src := img_element.get("src")) and validators.url(img_src):
            img_src = img_src.split("?")[0]
            img_elements_with_src.append((img_src, img_element))
        elif img_src := (img_element.get("data-src") or img_element.get("srcset")):
            img_src = img_src.split("?")[0]
            img_elements_with_src.append((img_src, img_element))
    if not img_elements_with_src:
        return []
    for image in input_images:
        image_outside_article = False
        for url in image.urls:
            url = url.split("?")[0]
            img_elements_with_src = sorted(
                img_elements_with_src, key=lambda src: SequenceMatcher(None, src[0], url).ratio(), reverse=True
            )
            _, most_similar_image = img_elements_with_src[0]
            figure_caption_text = generic_nodes_to_text(caption_selector(most_similar_image))
            figure_img_alt = alt_selector(most_similar_image)
            caption = ""
            for text_element in figure_caption_text:
                caption += re.sub(r"\s+", " ", text_element)
            if not image.caption:
                image.caption = caption.strip()
            if figure_authors := author_selector(most_similar_image):
                figure_authors_text = generic_author_parsing(generic_nodes_to_text(figure_authors))
                if figure_authors_text:
                    image.authors = figure_authors_text
            if author_pattern and caption and not image.authors and (match := re.search(author_pattern, caption)):
                image.authors = generic_author_parsing(match.group("credits"))
            if figure_img_alt:
                image.description = figure_img_alt[0].strip()
            if compare_html_element_positions(most_similar_image, first_paragraph):
                image.is_cover = True
            if (not compare_html_element_positions(most_similar_image, last_paragraph)) or (
                upper_boundary is not None and compare_html_element_positions(most_similar_image, upper_boundary)
            ):
                image_outside_article = True
                break
        if not image_outside_article:
            filtered_list.append(image)
    return filtered_list


def compare_html_element_positions(element: lxml.html.HtmlElement, other: lxml.html.HtmlElement) -> bool:
    """
    Compares the relative position of element and other within the document. Returns True if element comes first in the
    document, otherwise returns False
    @param element: HtmlElement, that is checked to be first
    @param other: HtmlElement, that is checked to be second
    @return: True, if element comes before other, otherwise False
    """
    # Build list of ancestors
    ancestors = [element]
    other_ancestors = [other]
    while ancestors[-1].getparent() is not None:
        ancestors.append(ancestors[-1].getparent())
    while other_ancestors[-1].getparent() is not None:
        other_ancestors.append(other_ancestors[-1].getparent())

    # Compare ancestors from the root down to find the first point of divergence
    for ancestor1, ancestor2 in zip(reversed(ancestors), reversed(other_ancestors)):
        if ancestor1 != ancestor2:
            # The elements have a different ancestor, compare their relative position
            parent = ancestor1.getparent()
            if parent is not None:
                children = list(parent)
                # If the ancestor of element lies before the ancestor of other, return True
                return children.index(ancestor1) < children.index(ancestor2)
            raise ValueError("The two elements do not have the same root element")
    # One element must be the parent of the other
    return len(ancestors) < len(other_ancestors)


def load_images_from_html(
    publisher_domain: str, doc: lxml.html.HtmlElement, image_selector: Union[CSSSelector, XPath] = XPath("//img")
) -> List[Image]:
    """
    Loads all img elements in the document structure and returns them as a list
    @param publisher_domain: the domain of the publisher, needed to fix relative URLs
    @param doc: The html document of the article
    @param image_selector: Selector selecting all relevant img elements. Defaults to selecting all
    @return: list of Fundus Images
    """
    image_list = []
    img_elements = image_selector(doc)
    if not img_elements:
        return image_list
    for img_element in img_elements:
        urls = [img_element.get("src"), img_element.get("data-src"), img_element.get("srcset")]
        urls = [url for url in urls if url and validators.url(url)]
        if not urls:
            continue
        url = urls[0]
        image_list.append(Image(urls=[preprocess_url(url, publisher_domain)]))
    return image_list


def merge_duplicate_images(image_list: List[Image], similarity_threshold: float = 0.8) -> List[Image]:
    """
    Given a list of Fundus Images, the list is collapsed by aggregating images based on URL similarity. Also, unique
    captions are considered to be separate images.
    @param image_list: list of Fundus Images
    @param similarity_threshold: ratio of minimum URL similarity for images to be considered the same
    @return: list of aggregated images
    """
    merged_list = []
    merged_images = set()
    for i in range(0, len(image_list)):
        image = image_list[i]
        if image in merged_images:
            continue
        urls = set(image.urls)
        is_cover = image.is_cover
        caption = image.caption
        description = image.description
        authors = image.authors
        for j in range(i + 1, len(image_list)):
            current_image = image_list[j]
            if current_image in merged_images:
                continue
            if SequenceMatcher(None, image.urls[0], current_image.urls[0]).ratio() >= similarity_threshold:
                if caption and image.caption and caption != image.caption:
                    # Images with different captions are likely different images
                    continue
                is_cover = is_cover or current_image.is_cover
                caption = caption or current_image.caption
                description = description or current_image.description
                authors = authors or current_image.authors
                urls.update(current_image.urls)
                merged_images.add(current_image)
        merged_list.append(
            Image(urls=list(urls), caption=caption, description=description, author=authors, is_cover=is_cover)
        )
    return merged_list


def image_extraction(
    url: str,
    doc: lxml.html.HtmlElement,
    paragraph_selector: Union[CSSSelector, XPath],
    image_selector: Union[CSSSelector, XPath] = XPath("//img"),
    upper_boundary_selector: Union[CSSSelector, XPath] = XPath("//main"),
    caption_selector: Union[CSSSelector, XPath] = XPath("./ancestor::figure//figcaption"),
    alt_selector: Union[CSSSelector, XPath] = XPath("./@alt"),
    author_selector: Union[CSSSelector, XPath] = XPath(
        "(./ancestor::figure//*[(contains(@class, 'copyright') or contains(@class, 'credit')) and text()])[1]"
    ),
    author_pattern: Optional[Pattern] = None,
    similarity_threshold: float = 0.8,
):
    """
    This function serves as an intermediary between the utility code and the parsers in an effort to make the utility
    functions easily and flexibly usable.
    @param url: URL of the article
    @param doc: The html document of the article
    @param paragraph_selector: Selector used to select the paragraphs of the article.
    @param image_selector: Selector selecting all relevant img elements. Defaults to selecting all
    @param upper_boundary_selector: A selector referencing an element to be considered as the upper boundary. All img
    elements before this element will be ignored.
    @param caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element
    @param alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
    @param author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
    figure with copyright or credit in its class attribute.
    @param author_pattern: If the authors are only mentioned in the caption, a regex expression can be used to match the
    authors. A captioning group named 'credits' should be used.
    @param similarity_threshold: ratio of minimum URL similarity for images to be considered the same
    @return: list of Images contained within the article
    """

    publisher_domain = urlparse(url).netloc
    image_list = load_images_from_html(publisher_domain=publisher_domain, doc=doc, image_selector=image_selector)
    image_list = extract_image_data_from_html(
        doc=doc,
        input_images=image_list,
        paragraph_selector=paragraph_selector,
        upper_boundary_selector=upper_boundary_selector,
        caption_selector=caption_selector,
        alt_selector=alt_selector,
        author_selector=author_selector,
        author_pattern=author_pattern,
    )
    return merge_duplicate_images(image_list, similarity_threshold=similarity_threshold)
