import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class BusinessInsiderDEParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 11, 24)
        _summary_selector = CSSSelector("article div.bi-bulletpoints li, article div.bi-bulletpoints > p")
        _subheadline_selector = CSSSelector("article > div > h2, article > div > h3")
        _paragraph_selector = XPath(
            """
            //article
            //div[
                contains(@class, 'article-body') 
                or contains(@class, 'piano-article')]
            /p[
                not(ancestor::*[@class='bi-bulletpoints']
                    or mark[@class='has-inline-color has-cyan-bluish-gray-color']
                    or @class='has-text-align-right')]
            """
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords")) or generic_topic_parsing(
                self.precomputed.ld.bf_search("keywords")
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//img[not(contains(@class, 'size-thumbnail-square'))]"),
            )

    class V2(V1):
        # lists consisting of links only ("Mehr zum Thema ...") are related-article teasers, not content
        _link_list = "ul[not(li[not(span[count(*)=1][a][normalize-space(.)=normalize-space(a)])])]"
        _summary_selector = CSSSelector("section.ods-c-bulletpoints li")
        _subheadline_selector = XPath(
            f"""
            //div[@itemprop='articleBody']/h3[contains(@class, 'ods-c-heading')]
                [not(following-sibling::*[not(contains(@class, 'ods-ads'))][1][self::{_link_list}])]
            | //div[@itemprop='articleBody']/details//h3[contains(@class, 'ods-c-axel-info-block__title')]
            """
        )
        _paragraph_selector = XPath(
            f"""
            //div[@itemprop='articleBody']/p[contains(@class, 'ods-a-body-text')]
                [not(starts-with(normalize-space(.), 'Disclaimer:'))]
            | //div[@itemprop='articleBody']/ul[not(self::{_link_list})]/li
            | //div[@itemprop='articleBody']/details//p[contains(@class, 'ods-o-frame-in-text__paragraph')]
            | //div[@itemprop='articleBody']/div[contains(@class, 'ods-o-faq')]
                //*[contains(@class, 'ods-m-faq-list-item__question-text')
                    or parent::div[contains(@class, 'ods-m-faq-list-item__answer')]]
            """
        )

        @attribute
        def authors(self) -> List[str]:
            persons = {
                person.get("@id"): person.get("name")
                for person in self.precomputed.ld.xpath_search("Person")
                if isinstance(person, dict)
            }
            authors = []
            for author in self.precomputed.ld.bf_search("author") or []:
                if isinstance(author, dict):
                    author = author.get("name") or persons.get(author.get("@id"))
                if author:
                    authors.append(author)
            return generic_author_parsing(authors)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='ods-c-article-photo']//img"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'ods-o-article-photo__figure')]"
                    "//span[contains(@class, 'ods-a-caption')]"
                ),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'ods-o-article-photo__figure')]"
                    "//div[contains(@class, 'ods-a-source-photo')]"
                ),
            )
