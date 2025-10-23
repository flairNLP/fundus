import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class KlasseGegenKlasseParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("article p, main article p, .post-content p, .entry-content p, .content p")
        _summary_selector = CSSSelector(
            "article .entry-content > p:first-child, article > p:first-child, .post-content > p:first-child"
        )
        _subheadline_selector = CSSSelector("article h2, .entry-content h2, .post-content h2")

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
            # 1) nur Meta (kein LD)
            res = generic_author_parsing(self.precomputed.meta.get("author"))
            if res:
                return res

            # 2) DOM-Fallbacks (WP-typisch)
            nodes = self.precomputed.doc.xpath(
                "//a[@rel='author']/text()"
                " | //span[contains(@class,'author')]//a/text()"
                " | //div[contains(@class,'author')]//a/text()"
                " | //div[contains(@class,'byline')]//a/text()"
                " | //span[contains(@class,'byline')]//a/text()"
                " | //a[contains(@href,'/autor/') or contains(@href,'/author/')]/text()"
            )
            vals = [t.strip() for t in nodes if t and t.strip()]
            seen, out = set(), []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    out.append(v)
            return out

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            # 1) Meta
            for cand in (
                self.precomputed.meta.get("article:published_time"),
                self.precomputed.meta.get("og:article:published_time"),
                self.precomputed.meta.get("date"),
            ):
                dt = generic_date_parsing(cand)
                if dt:
                    return dt

            # 2) <time datetime>
            for val in self.precomputed.doc.xpath("//time[@datetime]/@datetime"):
                dt = generic_date_parsing(val)
                if dt:
                    return dt

            # 3) sichtbarer Datumstext (inkl. dd.mm.yyyy)
            texts: list[str] = []
            texts += [t.strip() for t in self.precomputed.doc.xpath("//time//text()") if t and t.strip()]
            texts += [
                t.strip()
                for t in self.precomputed.doc.xpath(
                    "//*[contains(@class,'date') or contains(@class,'datum') or contains(@class,'entry-date') "
                    "or contains(@class,'meta-date') or contains(@class,'posted-on') or contains(@class,'post-meta')]//text()"
                )
                if t and t.strip()
            ]

            for t in texts:
                dt = generic_date_parsing(t)
                if dt:
                    return dt

            m = None
            for t in texts:
                m = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{4})(?:\s+(\d{1,2}:\d{2}))?\b", t)
                if m:
                    d, tm = m.group(1), m.group(2)
                    try:
                        if tm:
                            return datetime.strptime(f"{d} {tm}", "%d.%m.%Y %H:%M")
                        return datetime.strptime(d, "%d.%m.%Y")
                    except ValueError:
                        pass

            # 4) notfalls Roh-HTML
            m = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", self.precomputed.html or "")
            if m:
                try:
                    return datetime.strptime(m.group(1), "%d.%m.%Y")
                except ValueError:
                    pass

            # 5) optional: modified als Fallback
            for cand in (
                self.precomputed.meta.get("article:modified_time"),
                self.precomputed.meta.get("og:updated_time"),
            ):
                dt = generic_date_parsing(cand)
                if dt:
                    return dt

            return None

        @attribute
        def topics(self) -> List[str]:
            # 1) Meta
            res = generic_topic_parsing(
                self.precomputed.meta.get("keywords") or self.precomputed.meta.get("news_keywords")
            )
            if res:
                return res

            # 2) DOM: WP-typische Orte + Permalinks
            nodes = self.precomputed.doc.xpath(
                "//a[@rel='tag']/text() | //a[@rel='category tag']/text()"
                " | //div[contains(@class,'tags') or contains(@class,'tags-links') or contains(@class,'post-tags') "
                "    or contains(@class,'cat-links') or contains(@class,'post-categories') "
                "    or contains(@class,'entry-taxonomy') or contains(@class,'entry-taxonomies')]//a/text()"
                " | //a[contains(@href,'/schlagwort/') or contains(@href,'/thema/') or contains(@href,'/kategorie/') "
                "      or contains(@href,'/tag/') or contains(@href,'/category/')]/text()"
                " | //meta[@property='article:tag']/@content"
            )
            vals = [s.strip().lstrip("#") for s in nodes if s and s.strip()]

            seen, out = set(), []
            for v in vals:
                if v not in seen:
                    seen.add(v)
                    out.append(v)
            return out
