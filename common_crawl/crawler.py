import urllib.parse
from datetime import datetime
from functools import partial
from typing import Dict, Set, Generator, Optional, Literal
from urllib.parse import urlparse

import fastwarc
import requests
from dotmap import DotMap
from ftfy import guess_bytes

from common_crawl.iterator import CCNewsIterator
from html_parser import BaseParser
from stream import StreamLine, SupplyLayer, UnaryLayer, BaseLayer


class Article(DotMap):

    def __init__(self, url: str, crawl_date: datetime, /, **kwargs):
        super(Article, self).__init__(**kwargs)
        self.url = url
        self.crawl_date = crawl_date
        self.exception = None


def supply(warc_path: str, domains):
    with requests.Session() as session:
        response = session.get(warc_path, stream=True)
        for warc in fastwarc.ArchiveIterator(response.raw,
                                             record_types=int(fastwarc.WarcRecordType.response)):

            url = str(warc.headers['WARC-Target-URI'])
            parsed_url = urlparse(url)

            if parsed_url.hostname in domains:
                warc.freeze()
                yield warc


def parse(record: fastwarc.WarcRecord,
          mapping: Dict[str, Dict[str, BaseParser]],
          exception_handling) -> DotMap:
    # extract url
    url = str(record.headers['WARC-Target-URI'])
    parsed_url = urlparse(url)

    # setup article
    article = Article(url, record.record_date)

    # get parser
    domain = mapping.get(parsed_url.hostname)
    min_path = min(domain.keys(), key=lambda x: abs(len(x) - len(parsed_url.path)))
    if not (parser := domain[min_path]):
        # TODO: define default
        pass

    # extract decode html from record
    raw_body = record.reader.read()
    try:
        article.html = str(raw_body, encoding=record.http_charset)
    except (UnicodeDecodeError, TypeError):
        article.html = guess_bytes(raw_body)[0]

    if article.html:

        try:
            extracted_information = parser.parse(article.html)
            article.update(extracted_information)

            # TODO: benchmark
        except Exception as exc:
            if exception_handling == 'catch':
                article.exception = exc
            elif exception_handling == 'raise':
                raise exc


class Crawler:

    def __init__(self, server_address: str = 'https://data.commoncrawl.org/'):
        self.server_address = server_address
        self.news_iter = CCNewsIterator()

    def crawl(self,
              mapping: Dict[str, Optional[BaseParser]],
              start: datetime = None,
              end: datetime = None,
              exception_handling: Literal['suppress', 'catch', 'raise'] = 'catch',
              layers: Optional[BaseLayer] = None) -> Generator[DotMap, None, None]:

        parsed_mapping: Dict[str, Set[urllib.parse.ParseResult]] = dict()

        for domain, func in mapping.items():
            if '//' not in domain:
                # add default http schema if not present so urlparse works properly.
                # Otherwise, netloc and path are wrong
                domain = 'https://' + domain
            parsed_domain = urlparse(domain)

            if not (tmp := parsed_mapping.get(parsed_domain.hostname, dict())):
                parsed_mapping[parsed_domain.hostname] = tmp

            if tmp.get(path := parsed_domain.path):
                raise ValueError
            else:
                tmp[path] = func

        part_supply = partial(supply, domains=parsed_mapping.keys())
        part_parse = partial(parse, mapping=parsed_mapping, exception_handling=exception_handling)
        warc_paths = self.news_iter.get_list_of_warc_path(self.server_address, start, end)

        supplier_layer = SupplyLayer(target=part_supply, size=20, name='Supply Layer')
        parser_layer = UnaryLayer(target=part_parse, size=40, name='Parser Layer')

        with StreamLine([supplier_layer, parser_layer] + layers) as stream:
            yield from stream.imap(warc_paths)
