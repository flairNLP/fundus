from collections import defaultdict
from datetime import datetime
from functools import partial
from math import ceil
from multiprocessing import cpu_count
from typing import Dict, Generator, Optional, Literal
from urllib.parse import urlparse

import fastwarc
import requests
from dotmap import DotMap
from ftfy import guess_bytes

from src.common_crawl.iterator import CCNewsIterator
from src.html_parser import BaseParser
from stream import StreamLine, SupplyLayer, UnaryLayer


class Article(DotMap):

    def __init__(self, url: str, crawl_date: datetime, /, **kwargs):
        super(Article, self).__init__(**kwargs)
        self.url = url
        self.crawl_date = crawl_date
        self.exception: Optional[Exception] = None


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
            return article

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
              exception_handling: Literal['suppress', 'catch', 'raise'] = 'raise') -> Generator[DotMap, None, None]:

        parsed_mapping: defaultdict[str, dict[(str, BaseParser)]] = defaultdict(dict)

        for domain, func in mapping.items():
            if '//' not in domain:
                # add default http schema if not present so urlparse works properly.
                # Otherwise, netloc and path are wrong
                domain = 'https://' + domain
            parsed_domain = urlparse(domain)
            if func is None:
                pass
            elif issubclass(type(func), BaseParser):
                parsed_mapping[parsed_domain.netloc][parsed_domain.path] = func
            else:
                raise ValueError(f"Got unexpected parser value for '{domain}'")

        part_supply = partial(supply, domains=parsed_mapping.keys())
        part_parse = partial(parse, mapping=parsed_mapping, exception_handling=exception_handling)
        warc_paths = [self.news_iter.get_list_of_warc_path(self.server_address, start, end)[0]]

        max_process: int = cpu_count() - 1
        supply_size: int = min(ceil(max_process / 4), len(warc_paths))
        parser_size: int = min(max_process - supply_size, supply_size * 4)

        print(supply_size, parser_size)

        supplier_layer = SupplyLayer(target=part_supply, size=supply_size, name='Supply Layer')
        parser_layer = UnaryLayer(target=part_parse, size=parser_size, name='Parser Layer')

        with StreamLine([supplier_layer, parser_layer]) as stream:
            yield from stream.imap(warc_paths)
