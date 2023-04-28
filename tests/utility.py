import datetime
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple, Type, Union

from typing_extensions import Self

from fundus import PublisherCollection
from fundus.parser import BaseParser
from fundus.publishers.base_objects import PublisherEnum
from tests.resources.parser.test_data import __module_path__ as test_resource_path


@dataclass
class HTMLFile:
    content: str
    crawl_date: Union[datetime.date, datetime.datetime]
    publisher: PublisherEnum
    encoding: str = "utf-8"

    @property
    def path(self) -> Path:
        return test_resource_path / Path(
            f"{type(self.publisher).__name__.lower()}/"
            f"{self.publisher.name}_{self.crawl_date.strftime('%Y_%m_%d')}.html.gz"
        )

    @staticmethod
    def _parse_path(path: Path) -> Tuple[PublisherEnum, datetime.date]:
        name = path.name
        assert "." in name
        desc = str(name).split(".")[0].split("_")
        publisher_name = desc.pop(0)
        date = datetime.date(*map(int, desc))
        return PublisherCollection[publisher_name], date

    @classmethod
    def load(cls, path: Path) -> Self:
        with open(path, "rb") as html_file:
            compressed_file = html_file.read()
        decompressed_content = gzip.decompress(compressed_file)
        content = decompressed_content.decode(encoding=cls.encoding)
        publisher, date = cls._parse_path(path)
        return cls(content=content, crawl_date=date, publisher=publisher)

    def write(self) -> None:
        with open(self.path, "wb") as file:
            file.write(gzip.compress(bytes(self.content, self.encoding)))


def load_html_mapping(publisher: PublisherEnum) -> Dict[Type[BaseParser], HTMLFile]:
    html_paths = (test_resource_path / Path(f"{type(publisher).__name__.lower()}")).glob(f"{publisher.name}*.html.gz")
    html_files = [HTMLFile.load(path) for path in html_paths]
    html_mapping: Dict[Type[BaseParser], HTMLFile] = {}
    for html_file in html_files:
        version = publisher.parser(html_file.crawl_date)
        if html_mapping.get(type(version)):
            raise KeyError(f"Duplicate html files for '{publisher}' and version {type(version).__name__}")
        html_mapping[type(version)] = html_file
    return html_mapping


def generate_json_path(publisher: PublisherEnum) -> Path:
    relative_file_path = Path(f"{publisher.__class__.__name__.lower()}/{publisher.name}.json")
    return test_resource_path / relative_file_path


def load_json(publisher: PublisherEnum) -> Dict[str, Dict[str, Dict[str, Any]]]:
    absolute_path = generate_json_path(publisher)

    with open(absolute_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return data
    else:
        raise ValueError("Unknown json format")
