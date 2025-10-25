from datetime import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class HeiseParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//article[not(@data-component='TeaserContainer')]//p[@class='a-article-header__lead'] | //article[not(@data-component='TeaserContainer')]//div[@id='lead']/p"
        )
        _subheadline_selector = XPath(
            "//article[not(@data-component='TeaserContainer')]//h3[contains(@class,'subheading')] | //article[not(@data-component='TeaserContainer')]//h2[@class='heading-h2 replaced-h1']"
        )
        _paragraph_selector = XPath(
            "//div[contains(class, article-content)]/p[not(@class"
            " or ((string-length(text()) < 3) and (contains(text(), '(') or contains(span, '(')))"
            " or contains(text(), '=== Anzeige / Sponsorenhinweis')"
            " or contains(text(), 'Tipp: Wir sind bei WhatsApp!')"
            " or contains(a, 'heise+ abonnieren')"
            " or contains(text(), '► '))"
            " or @class='antwort rte__abs--antwort'"
            " or @class='frage rte__abs--frage'"
            " or @class='json-ld-paid-content-marker'] "
            " | //div[contains(class, article-content)]//ul["
            "@class='rte__list rte__list--unordered' or @class='boxtext']/li | "
            # The selectors below this line are specific for heise's blog: techstage.de
            "//div[@class='ringCommonDetail ringBlockType-paragraph ']/p"
            " | //div[@class='ringCommonDetail ringBlockType-paragraph ']//ul/li"
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
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            # There some (rare) cases there are some images that are not being extracted with this, because they are
            # referenced by relative URLs. e.g.
            # https://www.heise.de/hintergrund/Zahlen-bitte-136199-Eris-Der-Grund-warum-Pluto-kein-Planet-mehr-ist-9993800.html
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath(
                    "//h1[@class='article-headline ' or contains(@class, 'a-article-header__title')]"
                ),
                image_selector=XPath(
                    "//div[@class='article-image__gallery-container']//img|"
                    "//div[@class='image-container']//img|"
                    "//div[@class='article-layout__content']//figure[not(@class)]//noscript//img"
                ),
                caption_selector=XPath(
                    "./ancestor::figure//p[@class='a-caption__text']|"
                    "./ancestor::figure//div[@class='text']|"
                    "./ancestor::div[@class='article-gallery ']//span[@class='caption']"
                ),
                author_selector=XPath(
                    "./ancestor::figure//p[@class='a-caption__source']|"
                    "./ancestor::div[@class='article-gallery ']//span[@class='copyright']"
                ),
            )
