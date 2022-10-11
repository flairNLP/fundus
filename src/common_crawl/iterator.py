import gzip
import re
import typing
from datetime import datetime

import fastwarc
import more_itertools
import requests
from dateutil.rrule import rrule, MONTHLY
from fastwarc.warc import ArchiveIterator, WarcRecordType


class CCNewsIterator:

    def __init__(self, session: requests.Session = None):
        self._session: requests.Session = session if session else requests.Session()

    def _get_warc_paths(self, start, end, server_address) -> typing.List[str]:
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

        date_sequence: typing.List[datetime] = [dt for dt in rrule(MONTHLY, dtstart=start_date, until=end_date)]
        filtered_dates = list(filter(lambda date: end.replace(day=1) >= date >= start.replace(day=1), date_sequence))
        urls = [server_address + f"crawl-data/CC-NEWS/{date.strftime('%Y/%m')}/warc.paths.gz"
                for date in filtered_dates]

        warc_paths = list(more_itertools.flatten(
            [gzip.decompress(self._session.get(url).content).decode('utf-8').split()
             for url in urls])
        )

        start_strf = start.strftime('%Y%m%d%H%M%S')
        end_strf = end.strftime('%Y%m%d%H%M%S')

        return sorted([server_address + warc_path
                       for warc_path in
                       filter(lambda path: start_strf <= date_pattern.search(path)['date'] <= end_strf, warc_paths)],
                      reverse=True)

    def get_list_of_warc_path(self,
                              server_address: str,
                              start: datetime = None,
                              end: datetime = None) -> typing.List[str]:

        if start > end:
            raise ValueError('Start date has to be <= end date')

        return self._get_warc_paths(start, end, server_address)

    def iterate_warc_files(self,
                           server_address: str,
                           start: datetime = None,
                           end: datetime = None,
                           record_types: WarcRecordType = None) -> typing.Generator[fastwarc.WarcRecord, None, None]:

        for warc_path in self.get_list_of_warc_path(server_address, start, end):
            response = self._session.get(warc_path, stream=True)
            yield from ArchiveIterator(response.raw, record_types=int(record_types) if record_types else None)