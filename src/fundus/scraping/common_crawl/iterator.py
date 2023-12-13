import gzip
import re
from datetime import datetime
from typing import List, Iterator

import fastwarc
import more_itertools
import requests
from dateutil.rrule import rrule, MONTHLY
from fastwarc.warc import ArchiveIterator, WarcRecordType


class CCNewsIterator:

    def __init__(self, session: requests.Session = None, server_address: str = "https://data.commoncrawl.org/"):
        self.session: requests.Session = session if session else requests.Session()
        self.server_address = server_address

    def get_list_of_warc_path(self,
                              start: datetime = None,
                              end: datetime = None) -> List[str]:

        date_pattern: re.Pattern = re.compile('CC-NEWS-(?P<date>\d{14})-\d{5}')

        start_date = datetime.strptime('2016/08', '%Y/%m')
        end_date = datetime(datetime.today().year, datetime.today().month, datetime.today().day)

        if not start:
            start = start_date
        else:
            start = start_date if start < start_date else start

        if not end:
            end = end_date
        else:
            end = end_date if end > end_date else end

        if start > end:
            raise ValueError('Start date has to be <= end date. '
                             'The default, and earliest possible, start date is 2016/08')

        date_sequence: List[datetime] = [dt for dt in rrule(MONTHLY, dtstart=start_date, until=end_date)]
        filtered_dates = list(filter(lambda date: end.replace(day=1) >= date >= start.replace(day=1), date_sequence))
        urls = [self.server_address + f"crawl-data/CC-NEWS/{date.strftime('%Y/%m')}/warc.paths.gz"
                for date in filtered_dates]

        warc_paths = list(more_itertools.flatten(
            [gzip.decompress(self.session.get(url).content).decode('utf-8').split()
             for url in urls])
        )

        start_strf = start.strftime('%Y%m%d%H%M%S')
        end_strf = end.strftime('%Y%m%d%H%M%S')

        return sorted([self.server_address + warc_path
                       for warc_path in
                       filter(lambda path: start_strf <= date_pattern.search(path)['date'] <= end_strf, warc_paths)],
                      reverse=True)

    def iterate_warc_files(self,
                           start: datetime = None,
                           end: datetime = None,
                           record_types: WarcRecordType = WarcRecordType.response) -> Iterator[fastwarc.WarcRecord]:

        for warc_path in self.get_list_of_warc_path(start, end):
            response = self.session.get(warc_path, stream=True)
            yield from ArchiveIterator(response.raw, record_types=int(record_types))
