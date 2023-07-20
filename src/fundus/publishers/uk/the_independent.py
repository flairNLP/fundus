import datetime
import re
from typing import List, Match, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath


from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)

from fundus.parser.data import TextSequence


class TheIndependentParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("article div[id='main'] > p")
        _summary_selector = CSSSelector("header[id='articleHeader'] h2 > p")
        #_summary_selector = CSSSelector("header[id='articleHeader'] h2")

        """
        The _summary_selector does not work like so. The summary usually is a h2 element, 
        but it does not have a .text itself but instead contains a p element inside, like e.g.:
        
        <header id="articleHeader" class="sc-qvufca-5 hnKqFj">...
            <h1 class="sc-1xt8011-0 sc-qvufca-2 eLpUOs eBBoiW">Powerball: Can the winner of $1.02bn jackpot remain anonymous?</h1>
            <h2 class="sc-aeekvc-0 eKSXmp">
                <p>The winning $1.02bn Powerball ticket was claimed in California </p>
            </h2>
        <\header>
        
        Maybe because this is not how headings and paragraphs should be used, it seems like in the parsed html object, 
        the parent of p is not h2, but one of the divs.
        I wrote a "hacky" way of getting the right of the (mostly 3 but sometimes 2) p elements, see below. 
        But of course, this should be put into the CSSSelector itself.
        
        However, sometimes the h2 DOES have a text, e.g.:
            <h2 class="sc-aeekvc-0 eKSXmp">Lionesses captain Millie Bright will wear the ‘inclusion’, ‘Indigenous People’ 
                and ‘gender equality’ armbands during the group stage.
            </h2>
        
        But, when I tried to use the SCCCSelector like so: CSSSelector("header[id='articleHeader'] h2"), 
        I don't know why, but the whole article text got placed into the body.summary.
        
        """


        @attribute
        def body(self) -> ArticleBody:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector)
            if len(body.summary) == 0:
                article_header_paragraphs = CSSSelector("header[id='articleHeader'] p")(self.precomputed.doc)
                for p in article_header_paragraphs:
                    if p.getprevious().tag == "h2":
                        body.summary = TextSequence([p.text])
            return body

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

