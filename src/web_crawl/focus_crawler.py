
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

from src.common_crawl.iterator import CCNewsIterator
from src.html_parser import BaseParser
from stream import StreamLine, SupplyLayer, UnaryLayer


def FocusCrawler():


    def __init__():
        pass

    def crawl(self,
              mapping: Dict[str, Optional[BaseParser]],
              start: datetime = None,
              end: datetime = None,
              exception_handling: Literal['suppress', 'catch', 'raise'] = 'raise',
              warc_cache_dir: str = None) -> Generator[DotMap, None, None]:

