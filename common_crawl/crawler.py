import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from multiprocessing import Queue
from typing import Dict, Set, List, Generator, Callable, Optional, Literal
from urllib.parse import urlparse

import fastwarc
import more_itertools
import requests
from ftfy import guess_bytes

from common_crawl.iterator import CCNewsIterator
from stream.streampool import QueueConsumer


@dataclass
class Article:
    url: str
    crawl_date: datetime
    html: str
    exception: Optional[Exception] = None


def supply(queue: Queue, warc_paths: List[str], domains):
    with requests.Session() as session:
        for path in warc_paths:
            response = session.get(path, stream=True)
            for warc in fastwarc.ArchiveIterator(response.raw,
                                                 record_types=int(fastwarc.WarcRecordType.response)):

                url = str(warc.headers['WARC-Target-URI'])
                parsed_url = urlparse(url)

                if parsed_url.hostname in domains:
                    warc.freeze()
                    queue.put(warc)


def consume(record: fastwarc.WarcRecord,
            mapping: Dict[str, Dict[str, Callable[[object], None]]],
            exception_handling):
    url = str(record.headers['WARC-Target-URI'])
    parsed_url = urlparse(url)

    if domain := mapping.get(parsed_url.hostname):

        min_path = min(domain.keys(), key=lambda x: abs(len(x) - len(parsed_url.path)))
        if not (parser_fnc := domain[min_path]):
            # TODO: define default
            pass

        raw_body = record.reader.read()
        try:
            fixed_text = str(raw_body, encoding=record.http_charset)
        except (UnicodeDecodeError, TypeError):
            fixed_text = guess_bytes(raw_body)[0]

        if fixed_text:
            article = Article(url=url,
                              crawl_date=record.record_date,
                              html=fixed_text)

            try:
                parser_fnc(article)
            except Exception as exc:
                if exception_handling == 'catch':
                    article.exception = exc
                elif exception_handling == 'raise':
                    raise exc


class Crawler:

    def __init__(self, server_address):
        self.server_address = server_address
        self.news_iter = CCNewsIterator()

    def icrawl(self,
               mapping: Dict[str, Callable[[Article], None]],
               start: datetime = None,
               end: datetime = None,
               exception_handling: Literal['suppress', 'catch', 'raise'] = 'catch') -> Generator[Article, None, None]:

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
        part_consume = partial(consume, mapping=parsed_mapping, exception_handling=exception_handling)
        warc_paths = self.news_iter.get_list_of_warc_path(self.server_address, start, end)
        path_chunks = more_itertools.distribute(20, warc_paths)

        cq = QueueConsumer(max_queue_size=10)
        yield from cq.consume_feed((part_supply, path_chunks), part_consume, max_process=40)
