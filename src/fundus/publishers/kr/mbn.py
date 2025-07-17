import pdb
import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class MBNParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_bloat_regex = r"^\[.*\]$"

        _paragraph_selector = XPath(
            f"//div[@itemprop='articleBody']//p[(normalize-space() or @class='br-wrap') and not(re:test(string(), '{_paragraph_bloat_regex}') or @class='summary_line') and text()]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath(
            "//div[@itemprop='articleBody']//p[@class='br-wrap' and not(text())]//*[self::b or (self::span and contains(@style, 'bold'))]"
        )
        _summary_selector = XPath("//div[contains(@class,'midtitle_text')]| //p[@class='summary_line']")

        _full_text_selector = XPath("//div[@itemprop='articleBody']")

        _article_author_selector = XPath("//li[@class='author']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            doc = None
            nodes = self._full_text_selector(self.precomputed.doc)
            if nodes and len(nodes) == 1:
                element = nodes[0]
                if element.xpath(".//p[normalize-space()]"):
                    for ad in element.xpath(".//div[contains(@class,'ad_wrap')]"):
                        parent = ad.getparent()
                        if parent is not None:
                            parent.remove(ad)
                if element.xpath("./self::div[@class='article_body']"):
                    # In case this uses the economy section layout, we need to transform <br> tags to paragraphs
                    doc = transform_breaks_to_paragraphs(element)
                else:
                    doc = transform_breaks_to_paragraphs(element, __class__="summary_line")
            return extract_article_body_with_selector(
                doc=doc if doc is not None else self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if not (
                author_string := generic_author_parsing(
                    self.precomputed.ld.xpath_search("NewsArticle//author", scalar=False)
                )
            ):
                authors = generic_author_parsing(
                    generic_nodes_to_text(self._article_author_selector(self.precomputed.doc))
                )
                return [re.sub(r"\s*기자\s*", "", author) for author in authors]
            return generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(
                self.precomputed.ld.xpath_search("NewsArticle//datePublished", scalar=True)
                or self.precomputed.meta.get("article:published_time")
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle//headline", scalar=True) or self.precomputed.meta.get(
                "og:title"
            )

        @attribute
        def images(self) -> List[Image]:
            author_pattern = re.compile(
                r"(?P<credits>\[사진(?:\s*출처)?\s*=\s*([^\]]+)\]|<\s*([^>]+?)\s*기자\s*>|사진\s*=\s*([^.\]\r\n<>]+)|\.[^.]+$)"
            )
            images = image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                lower_boundary_selector=XPath("//div[@id='refTotal']"),
                image_selector=XPath(
                    "//div[@itemprop='articleBody']//div[@class='thumb_area img' or @class='image']//img"
                ),
                caption_selector=XPath(
                    "./ancestor::div[@class='thumb_area img' or @class='image']//*[(self::span and @class='thum_figure_txt') or (self::p and @class='caption')]"
                ),
                alt_selector=XPath("./@alt"),
                author_selector=author_pattern,
            )

            author_bloat_pattern = re.compile(r"\s*([.\[\]<>()]|사진(\s*출처)?\s*=|기자\s*=|사진\s*I?)\s*")
            for img in images:
                for author in img.authors:
                    authors = list()
                    author = author_bloat_pattern.sub("", author).strip()
                    if author:
                        authors.append(author)
                    img.authors = authors

            return images
