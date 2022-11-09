import json
import re
from datetime import datetime
from typing import List

import feedparser
import lxml
import requests




def download_urls_from_sitemap(sitemap_url: str) -> List[str]:
    sitemap_html = requests.get(sitemap_url).content
    sitemap_tree = lxml.html.fromstring(sitemap_html)
    url_nodes = sitemap_tree.cssselect('url > loc')
    sitemap_urls = {node.text_content() for node in url_nodes}

    return sorted(list(sitemap_urls))


def download_urls_from_rss(rss_url: str) -> List[str]:
    rss_feed = feedparser.parse(rss_url)
    initial_urls = {entry["link"] for entry in rss_feed['entries']}
    cleaned_urls = {re.sub('#ref=rss', '', url_el) for url_el in initial_urls}
    return sorted(list(cleaned_urls))


def test_bz_parser():
    # This one is not in the right format!

    example_parser = BZParser()
 #   print(
 #       f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.mandatory_attributes)}'")

    current_sitemap = "https://www.berliner-zeitung.de/sitemap.current_date.xml"
    current_sitemap = current_sitemap.replace("current_date", datetime.utcnow().date().strftime('%Y-%m-%d'))

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_welt_parser():
    example_parser = DieWeltParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}', of which {', '.join(example_parser.mandatory_attributes)} are mandatory")

    current_sitemap = "https://www.ndr.de/sitemap112-newssitemap.xml"
    current_rss = "https://www.welt.de/feeds/latest.rss"

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_dw_parser():
    example_parser = DWParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.mandatory_attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"
    current_rss = "https://www.welt.de/feeds/latest.rss"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_focus_parser():
    example_parser = FocusParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.mandatory_attributes)}'")

    current_sitemap = "https://www.dw.com/de/sitemap-news.xml"
    current_rss = 'https://rss.focus.de/fol/XML/rss_folnews.xml'

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_mdr_parser():
    example_parser = MDRParser()
  #  print(
   # \    f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}', of which '{', '.join(example_parser.mandatory_attributes)}' are mandatory")

    current_sitemap = "https://www.mdr.de/news-sitemap.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_merkur_parser():
    example_parser = MerkurParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}', of which '{', '.join(example_parser.mandatory_attributes)}' are mandatory")

    current_rss = "https://www.merkur.de/welt/rssfeed.rdf"

    current_url_list = download_urls_from_rss(current_rss)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_ndr_parser():
    example_parser = NDRParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.mandatory_attributes)}'")

    current_sitemap = "https://www.ndr.de/sitemap112-newssitemap.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_ntv_parser():
    example_parser = NTVParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}', of which {', '.join(example_parser.mandatory_attributes)} are mandatory")

    current_sitemap = "https://www.n-tv.de/news.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


def test_faz_parser():
    example_parser = FAZParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}', of which {', '.join(example_parser.mandatory_attributes)} are mandatory")

    current_sitemap = "https://www.n-tv.de/news.xml"

    current_url_list = download_urls_from_sitemap(current_sitemap)
    for url_el in current_url_list:
        try:
            current_html = requests.get(url_el).text
            article = example_parser.parse(current_html)
            print("!")
        except json.JSONDecodeError:
            continue


if __name__ == '__main__':
    test_bz_parser()
