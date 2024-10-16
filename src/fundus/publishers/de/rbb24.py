import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class RBB24Parser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[contains(concat(' ', @class , ' '), ' textblock ')]/p")
        _summary_selector = XPath("//div[contains(concat(' ', @class , ' '), ' shorttext ')]/p")
        _subheadline_selector = XPath("//h4[contains(concat(' ', @class , ' '), ' texttitle ')]")
        _author_selector = CSSSelector("span.authorname")
        _date_selector = CSSSelector("div.lineinfo")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            article_body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )
            # If author was specified, the author is often credited after the last sentence of the summary:
            # "... . Von Max Mustermann". We need to remove this.
            # As XPath can only select whole subtrees, we need to remove it later,
            # because the html will look like:
            # <div class="shorttext">
            #   <p> Summary Text
            #     <i>Von Max Mustermann</i>
            #   </p>
            # </div>
            #
            # Check if author was specified and if the author was also credited:
            if len(self._author_selector(self.precomputed.doc)) > 0:
                # Get authors
                authors_list = self.authors()
                # Get summary as string
                summary = article_body.summary._data[0]
                # Make sure that we choose a period that is not the last character of string,
                # in case it was written like: "... . Von Max Mustermann."
                potential_end_of_summary = summary[: len(summary) - 1].rfind(".")
                potential_credits = summary[potential_end_of_summary + 2 : len(summary)]
                # Check whether the last sentence credits the author
                # Does the sentence start with "Von"
                if potential_credits.split(" ", 1)[0] == "Von":
                    authors_credited = True
                    # Are the authors credited ?
                    for author in authors_list:
                        if author not in potential_credits:
                            authors_credited = False
                            break
                    # Delete last sentence if this sentence just credits the authors
                    if authors_credited:
                        # As the string of the summary is a tuple we can't change it and need to create a new one
                        article_body.summary._data = (summary[: potential_end_of_summary + 1],)
            # Often articles end with "Sendung: rbb24 Abendschau, 30.04.2024, 19:30 Uhr" or
            # "Sendung: Der Tag, 26.04.2024, 19:15 Uhr" etc
            # We need to delete this last paragraph
            last_paragraph = article_body.sections[-1].paragraphs._data[-1]
            if last_paragraph.startswith("Sendung:"):
                # Make tuple to list to delete last element of list, to then make it a tuple again
                new_data_tuple = (article_body.sections[-1].paragraphs._data)[:-1]
                article_body.sections[-1].paragraphs._data = new_data_tuple
            return article_body

        @attribute
        def authors(self) -> List[str]:
            # check if author was specified
            if len(self._author_selector(self.precomputed.doc)) > 0:
                authors = self._author_selector(self.precomputed.doc)[0].text
                return generic_author_parsing(authors)
            else:
                return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            publishing_date_string = self._date_selector(self.precomputed.doc)[0].text
            # publishing_date_string will look like 'Do 25.04.24 | 13:47 Uhr'
            # need to get the date and time to pass it to the generic_date_parsing
            if publishing_date_string is not None:
                index = publishing_date_string.index("|")
                date_string = publishing_date_string[index - 9 : index - 1]
                time_string = publishing_date_string[index + 1 : index + 7]
                return generic_date_parsing(date_string + " " + time_string)
            else:
                return generic_date_parsing(None)

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")
