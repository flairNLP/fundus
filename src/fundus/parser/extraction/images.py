from __future__ import annotations

import re
from typing import (
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Set,
    Union,
    cast,
)
from urllib.parse import urljoin

import lxml.etree
import lxml.html
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.extraction.metadata import generic_author_parsing
from fundus.parser.extraction.text import generic_nodes_to_text
from fundus.parser.types.image import Dimension, Image, ImageURLError, ImageVersion
from fundus.utils.regex import _get_match_dict

logger = create_logger(__name__)


class DOM:
    def __init__(self, root: lxml.html.HtmlElement):
        self.root = root
        self._depth_first_index = {element: i for i, element in enumerate(root.iter())}

    def get_index(self, node: lxml.html.HtmlElement) -> int:
        return self._depth_first_index[node]


def image_author_parsing(authors: Union[str, List[str]]) -> List[str]:
    credit_keywords = [
        "Источник",
        "коллаж",
        "Джерело",
        "Фото",
        "колаж",
        "fotograf",
        "credits?",
        "quellen?",
        "bild(rechte)?",
        "sources?",
        r"(((f|ph)oto(graph)?s?|image|illustrations?|cartoons?|pictures?)\s*)+(by|:|courtesy)",
        "©",
        "– alle rechte vorbehalten",
        "copyright",
        "all rights reserved",
        "courtesy of",
        "＝",
    ]
    author_filter = re.compile(r"(?is)^(" + r"|".join(credit_keywords) + r"):?\s*")

    def clean(author: str):
        author = re.sub(r"^\((.*)\)$", r"\1", author).strip()
        # filtering credit keywords
        author = re.sub(author_filter, "", author, count=1)
        # filtering bloat follwing the author
        author = re.sub(r"(?i)/?copyright.*", "", author)
        return author.strip()

    if isinstance(authors, list):
        authors = [clean(author) for author in authors]
    else:
        authors = clean(authors)
    return generic_author_parsing(authors)


# https://regex101.com/r/MplUXL/2
# candidates are separated by a comma that may sit flush against the preceding url, e.g.
# 'a.jpg, b.jpg 2x'. only strip commas terminating a url, so that urls carrying commas of
# their own - CDN transformations like '.../w_300,h_200/img.jpg' - survive intact.
_srcset_pattern = re.compile(r"(?P<url>\S+?),*(?=\s|$)\s*(?P<descriptor>[0-9.]+[wx])?\s*,?\s*")


def parse_srcset(srcset: str) -> Dict[str, str]:
    # Updated regular expression to account for query parameters in URLs
    urls = {}
    for match in _srcset_pattern.finditer(srcset.strip()):
        url = match.group("url")
        descriptor = match.group("descriptor")  # Width (w) or pixel density (x)
        urls[descriptor or "1x"] = url
    # return sorted dict based on int value of descriptor
    return dict(sorted(urls.items(), key=lambda item: float(item[0][:-1])))


# that's the same as string(./attribute::*[ends-with(name(), '*')]) but LXML doesn't support the ends-with function
# these two selectors select the value of the first attribute found ending with src/srcset relative to the node
# as truing value
_srcset_selector = XPath(
    "./@*[substring(name(), string-length(name()) - string-length('srcset') + 1)  = 'srcset'][starts-with(., 'http') or starts-with(., '/')]"
)
_src_selector = XPath(
    "./@*[substring(name(), string-length(name()) - string-length('src') + 1)  = 'src'][starts-with(., 'http') or starts-with(., '/')]"
)


def parse_urls(node: lxml.html.HtmlElement) -> Optional[Dict[str, str]]:
    def get_longest_string(strings: List[str]) -> str:
        return sorted(strings, key=len)[-1]

    if srcset := cast(List[str], _srcset_selector(node)):
        return parse_srcset(get_longest_string(srcset))
    elif src := cast(List[str], _src_selector(node)):
        return {"1x": get_longest_string(src)}
    else:
        return None


class _DimensionCalculator:
    def __init__(
        self, width: Optional[float] = None, height: Optional[float] = None, ratio: Optional[float] = None
    ) -> None:
        self.width = width
        self.height = height
        self.ratio = ratio

    def calculate(
        self, width: Optional[float] = None, height: Optional[float] = None, dpr: Optional[float] = None
    ) -> Optional[Dimension]:
        if not (width or height):
            width = self.width
            height = self.height
        if dimension := Dimension.from_ratio(width, height, self.ratio):
            return dimension * (dpr or 1)
        return None


_media_param_pattern = re.compile(r"\(\s*(?P<param>[\w-]+)\s*:\s*(?P<value>[\d./]+)(?P<unit>[a-z]*)\)")
_width_x_height_pattern = re.compile(r"(?P<width>[0-9]+)x(?P<height>[0-9]+)")


def get_versions_from_node(
    source: lxml.html.HtmlElement, ratio: Optional[float], size_pattern: Optional[Pattern[str]]
) -> Set[ImageVersion]:
    if not (urls := parse_urls(source)):
        return set()

    # get min/max width
    query_width = None
    for param, value, descriptor in re.findall(_media_param_pattern, source.get("media", "").split(",")[0]):
        if param in ["min-width", "max-width"]:
            if descriptor != "px":
                logger.debug(f"Pixel calculation not implemented for {descriptor}")
            else:
                # with the assumption that there is only one max/min width per ',' seperated query and only
                # either min- or max-width
                query_width = f"{param}:{value}"

    # get width, height and init calculator
    if (src_width := source.get("width")) and src_width.replace(".", "", 1).isdigit():
        width = float(src_width or 0) or None
    else:
        width = None
    if (src_height := source.get("height")) and src_height.replace(".", "", 1).isdigit():
        height = float(src_height or 0) or None
    else:
        height = None
    if width and height:
        ratio = width / height
    calculator = _DimensionCalculator(width, height, ratio)

    versions = set()
    for descriptor, url in urls.items():
        kwargs: Dict[str, float] = {}
        if descriptor is not None:
            if match := re.search(r"(?P<multiplier>[0-9.]+)x", descriptor):
                kwargs["dpr"] = float(match.group("multiplier"))
            elif match := re.search(r"(?P<width>[0-9]+)(px|w)", descriptor):
                kwargs["width"] = float(match.group("width"))

        if size_pattern is not None and (
            match_dict := _get_match_dict(size_pattern, url, conversion=lambda x: float(x))
        ):
            kwargs.update(match_dict)
        elif not (calculator.width or kwargs.get("width")) and (match := re.search(_width_x_height_pattern, url)):
            kwargs.update({k: float(v) for k, v in match.groupdict().items() if v is not None})

        version = ImageVersion(
            url=url, query_width=query_width, size=calculator.calculate(**kwargs), type=source.get("type")
        )
        versions.add(version)

    return versions


_relative_source_selector = XPath("./ancestor::picture//source")


def parse_versions(img_node: lxml.html.HtmlElement, size_pattern: Optional[Pattern[str]] = None) -> List[ImageVersion]:
    # parse img
    if (
        (default_width := img_node.get("width"))
        and not default_width == "auto"
        and (default_height := img_node.get("height"))
        and not default_height == "auto"
        and not float(default_height) == 0.0
    ):
        ratio = float(default_width) / float(default_height)
    else:
        ratio = None

    versions = set()
    for source in _relative_source_selector(img_node) + [img_node]:
        for version in get_versions_from_node(source, ratio, size_pattern):
            versions.add(version)

    return sorted(versions)


class IndexedImageNode(NamedTuple):
    position: int
    content: lxml.html.HtmlElement
    is_cover: bool


def parse_image_nodes(
    image_nodes: List[IndexedImageNode],
    caption_selector: XPath,
    alt_selector: XPath,
    author_selector: Union[XPath, Pattern[str], List[Pattern[str]]],
    domain: Optional[str] = None,
    size_pattern: Optional[Pattern[str]] = None,
) -> Iterator[Image]:
    """Extract urls, caption, description and authors from a list of <img> nodes

    Args:
        image_nodes: Indexed <img> nodes to parse.
        caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element.
        alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
        author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
            figure with copyright or credit in its class attribute.
        domain: If set, the domain will be prepended to URLs in case they are relative
        size_pattern: Regular expression to select <width>, <height> and <dpr> from the image URL. The given regExp
            will be matched with re.findall and overwrites existing values. Defaults to None.

    Returns:
        List of Images
    """

    def nodes_to_text(nodes: List[Union[lxml.html.HtmlElement, str]]) -> Optional[str]:
        return " ".join(generic_nodes_to_text(nodes, normalize=True)) or None

    for position, node, is_cover in image_nodes:
        # parse URLs
        if not (versions := parse_versions(node, size_pattern)):
            continue

        # resolve relative URLs if domain is given
        if domain is not None:
            for version in versions:
                version.url = urljoin(domain, version.url)

        # parse caption
        caption = nodes_to_text(caption_selector(node))

        # parse description
        description = nodes_to_text(alt_selector(node))

        # parse authors

        authors = []
        if isinstance(author_selector, Pattern):
            author_selector = [author_selector]

        if isinstance(author_selector, list):
            for pattern in author_selector:
                # author is part of the caption
                if caption and (match := re.search(pattern, caption)):
                    authors = [match.group("credits")]
                    caption = re.sub(pattern, "", caption).strip() or None
                    break
            if not authors:
                for pattern in author_selector:
                    if description and (match := re.search(pattern, description)):
                        authors = [match.group("credits")]
                        break

        else:
            # author is selectable as node
            if author_nodes := author_selector(node):
                authors = generic_nodes_to_text(author_nodes, normalize=True)
        authors = image_author_parsing(authors)

        try:
            image = Image(
                versions=versions,
                caption=caption,
                authors=authors,
                description=description,
                is_cover=is_cover,
                position=position,
            )
        except ImageURLError as error:
            if node.attrib.get("loading") == "lazy":
                logger.debug("Skipping lazy loading image")
            else:
                logger.debug(error)
        else:
            yield image


class Bounds(NamedTuple):
    upper: int
    first_paragraph: Optional[int]
    lower: int


def determine_bounds(
    dom: DOM, paragraph_selector: XPath, upper_boundary_selector: XPath, lower_boundary_selector: Optional[XPath]
) -> Optional[Bounds]:
    def get_sorted_indices(nodes: List[lxml.html.HtmlElement]) -> List[int]:
        return sorted([dom.get_index(node) for node in nodes])

    # the getitem on upper_boundary_selector ensures that this throws an exception, if there are no
    # upper_boundary_node present, as well as removing excess ones.
    upper_boundary_nodes = [upper_boundary_selector(dom.root)[0]]
    paragraph_nodes = paragraph_selector(dom.root)
    lower_boundary_nodes = lower_boundary_selector(dom.root) if lower_boundary_selector else []

    sorted_indices = get_sorted_indices(upper_boundary_nodes + paragraph_nodes + lower_boundary_nodes)

    if len(sorted_indices) < 2:
        return None

    return Bounds(
        upper=sorted_indices[0],
        first_paragraph=paragraph_indices[0] if (paragraph_indices := get_sorted_indices(paragraph_nodes)) else None,
        lower=sorted_indices[-1],
    )


_og_url_selector = XPath("string(//meta[@property='og:url']/@content)")


def image_extraction(
    doc: lxml.html.HtmlElement,
    paragraph_selector: XPath,
    image_selector: XPath = XPath("//figure//img"),
    upper_boundary_selector: XPath = XPath("//main"),
    lower_boundary_selector: Optional[XPath] = None,
    caption_selector: XPath = XPath("./ancestor::figure//figcaption"),
    alt_selector: XPath = XPath("./@alt"),
    author_selector: Union[XPath, Pattern[str], List[Pattern[str]]] = XPath(
        "(./ancestor::figure//*[(contains(@class, 'copyright') or contains(@class, 'credit')) and text()])[1]"
    ),
    relative_urls: Union[bool, XPath] = False,
    size_pattern: Pattern[str] = re.compile(
        r"width([=-])(?P<width>[0-9.]+)|height([=-])(?P<height>[0-9.]+)|dpr=(?P<dpr>[0-9.]+|)"
    ),
) -> List[Image]:
    """Extracts images enriched with metadata from <dom> based on given selectors.

    The core idea behind this function is to select all images matching <image_selector> that lay between
    the first element selected by <upper_boundary_selector> and the last element of <lower_boundary_selector>
    or <paragraph_selector>. The hierarchy is determined by indexing all nodes of <doc> depth first.
    To enrich the selected images with metadata like 'caption', 'alt-description' or `authors`, one should make
    use of the corresponding selectors.

    Args:
        doc: The html document of the article.
        paragraph_selector: Selector used to select the paragraphs of the article.
        image_selector: Selector selecting all relevant img elements. Defaults '//figure//img'.
        upper_boundary_selector: A selector referencing an element to be considered as the upper boundary. All img
            elements before this element will be ignored.
        lower_boundary_selector: A selector referencing an element to be considered as the lower boundary. All img
            elements after this element will be ignored. Defaults to the last paragraph of an article.
        caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element.
        alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
        author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
            figure with copyright or credit in its class attribute.
        relative_urls: If True, the extractor assumes that image src URLs are relative and prepends the publisher
            domain
        size_pattern: Regular expression to select <width>, <height> and <dpr> from the image URL. The given regExp
            will be matched with re.findall and overwrites existing values. Defaults to None.

    Returns:
        A list of Images contained within the article

    """

    # index nodes df
    dom = DOM(doc)

    # determine bounds based on df index
    if not (bounds := determine_bounds(dom, paragraph_selector, upper_boundary_selector, lower_boundary_selector)):
        raise ValueError("Bounds could not be determined")

    if relative_urls:
        if isinstance(relative_urls, bool):
            selector = _og_url_selector
        else:
            selector = relative_urls
        if not (domain := selector(dom.root)):
            raise ValueError("Could not determine domain")
    else:
        domain = None

    image_nodes = [
        IndexedImageNode(position=position, content=node, is_cover=position < (bounds.first_paragraph or 0))
        for node in image_selector(doc)
        if bounds.upper < (position := dom.get_index(node)) < bounds.lower
    ]

    images = list(
        parse_image_nodes(
            image_nodes=image_nodes,
            caption_selector=caption_selector,
            alt_selector=alt_selector,
            author_selector=author_selector,
            domain=domain,
            size_pattern=size_pattern,
        )
    )

    return images
