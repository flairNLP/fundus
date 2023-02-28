import shutil
from collections import defaultdict
from datetime import datetime
from functools import partial
from math import ceil
from multiprocessing import cpu_count
from os import makedirs
from pathlib import Path
from typing import Dict, Generator, Optional, Literal, List
from urllib.parse import urlparse, quote_plus

import fastwarc
import requests
from dotmap import DotMap
from ftfy import guess_bytes

from src.parser.html_parser import BaseParser
from src.scraping.crawler.common_crawl.iterator import CCNewsIterator
from stream import StreamLine, SupplyLayer, UnaryLayer


def supply(warc_path: str, domains: List[str], warc_cache_path: Path):
    with requests.Session() as session:

        if warc_cache_path:
            if not warc_cache_path.exists():
                makedirs(warc_cache_path)
            file_name = quote_plus(warc_path)
            file_path = warc_cache_path / file_name

            if not file_path.is_file():
                with session.get(warc_path, stream=True) as response:
                    with file_path.open('wb+') as file:
                        shutil.copyfileobj(response.raw, file)

            stream = fastwarc.GZipStream(fastwarc.FileStream(str(file_path), 'rb'))

        else:
            stream = session.get(warc_path, stream=True).raw

        for warc in fastwarc.ArchiveIterator(stream,
                                             record_types=int(fastwarc.WarcRecordType.response)):

            # TODO: check digest
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
    article = DotMap()
    article.url = url
    article.crawl_date = record.record_date

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

        return article


class Crawler:

    def __init__(self, server_address: str = 'https://data.commoncrawl.org/'):
        self.server_address = server_address
        self.news_iter = CCNewsIterator()

    def crawl(self,
              mapping: Dict[str, Optional[BaseParser]],
              start: datetime = None,
              end: datetime = None,
              exception_handling: Literal['suppress', 'catch', 'raise'] = 'raise',
              warc_cache_dir: str = None) -> Generator[DotMap, None, None]:

        parsed_mapping: defaultdict[str, Dict[(str, BaseParser)]] = defaultdict(dict)

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

        part_supply = partial(supply, domains=parsed_mapping.keys(),
                              warc_cache_path=Path(warc_cache_dir) if warc_cache_dir else None)
        part_parse = partial(parse, mapping=parsed_mapping, exception_handling=exception_handling)
        warc_paths = self.news_iter.get_list_of_warc_path(self.server_address, start, end)

        max_process: int = cpu_count() - 1
        supply_size: int = min(ceil(max_process / 4), len(warc_paths))
        parser_size: int = min(max_process - supply_size, supply_size * 4)

        supplier_layer = SupplyLayer(target=part_supply, size=supply_size, name='Supply Layer')
        parser_layer = UnaryLayer(target=part_parse, size=parser_size, name='Parser Layer')

        with StreamLine([supplier_layer, parser_layer]) as stream:
            yield from stream.imap(warc_paths)
