import datetime
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple, Type, Union

from typing_extensions import Self

from fundus import PublisherCollection
from fundus.logging.logger import basic_logger
from fundus.parser import BaseParser
from fundus.publishers.base_objects import PublisherEnum
from tests.resources.parser.test_data import __module_path__ as test_resource_path


@dataclass
class HTMLTestFile:
    content: str
    crawl_date: Union[datetime.date, datetime.datetime]
    publisher: PublisherEnum
    encoding: str = "utf-8"

    @property
    def path(self) -> Path:
        return (
            test_resource_path
            / f"{type(self.publisher).__name__.lower()}"
            / f"{self.publisher.name}_{self.crawl_date.strftime('%Y_%m_%d')}.html.gz"
        )

    @staticmethod
    def _parse_path(path: Path) -> Tuple[PublisherEnum, datetime.date]:
        assert path.name.endswith(".html.gz")
        file_name: str = path.name.rsplit(".html.gz")[0]
        publisher_name, date = file_name.split("_", maxsplit=1)
        return PublisherCollection[publisher_name], datetime.datetime.strptime(date, "%Y_%m_%d").date()

    @classmethod
    def load(cls, path: Path, encoding: str = "utf-8") -> Self:
        """Loads an HTMLTestFile from the given path.

        The file at the location is expected to be a gzipped HTML file. The
        path syntax is defined as following:
            test_resource_path / <country_code> / <publisher_name>_<year>_<month>_<day>.html.gz
            with:
                <country_code>:         2-letter code, i.e. us for United States
                <publisher_name>:       the enum name, i.e. DW, FAZ, APNews
                <year>_<month>_<day>:   parsed date object, as when using date.strftime('%Y_%m_%d')


        Args:
            path:       The HTMLTestFile location
            encoding:   The encoding in which the file should be loaded

        Returns:
            A HTMLTestFile object loaded with the file given with <path>

        """
        with open(path, "rb") as html_file:
            compressed_file = html_file.read()
        decompressed_content = gzip.decompress(compressed_file)
        content = decompressed_content.decode(encoding=encoding)
        publisher, date = cls._parse_path(path)
        return cls(content=content, crawl_date=date, publisher=publisher, encoding=encoding)

    def write(self) -> None:
        with open(self.path, "wb") as file:
            file.write(gzip.compress(bytes(self.content, self.encoding)))


def load_html_test_file_mapping(publisher: PublisherEnum) -> Dict[Type[BaseParser], HTMLTestFile]:
    html_paths = (test_resource_path / Path(f"{type(publisher).__name__.lower()}")).glob(f"{publisher.name}*.html.gz")
    html_files = [HTMLTestFile.load(path) for path in html_paths]
    html_mapping: Dict[Type[BaseParser], HTMLTestFile] = {}
    for html_file in html_files:
        versioned_parser = publisher.parser(html_file.crawl_date)
        if html_mapping.get(type(versioned_parser)):
            raise KeyError(f"Duplicate html files for '{publisher}' and version {type(versioned_parser).__name__}")
        html_mapping[type(versioned_parser)] = html_file
    return html_mapping


def generate_parser_test_case_json_path(publisher: PublisherEnum) -> Path:
    relative_file_path = Path(f"{type(publisher).__name__.lower()}/{publisher.name}.json")
    return test_resource_path / relative_file_path


def load_test_case_data(publisher: PublisherEnum) -> Dict[str, Dict[str, Dict[str, Any]]]:
    absolute_path = generate_parser_test_case_json_path(publisher)

    with open(absolute_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return data
    else:
        raise ValueError(
            f"Received invalid JSON format for publisher {repr(publisher.name)}. Expected a JSON with a dictionary as root."
        )
