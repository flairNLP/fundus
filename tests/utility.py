import datetime
import gzip
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Dict, Type, Generic, TypeVar, Optional, Callable, cast

from typing_extensions import Self

from fundus import PublisherCollection
from fundus.parser import BaseParser
from fundus.publishers.base_objects import PublisherEnum
from scripts.generate_tables import supported_publishers_markdown_path
from tests.resources.parser.test_data import __module_path__ as test_resource_path

T = TypeVar("T")


@dataclass
class JSONFile(Generic[T]):
    path: Path
    encoder: Optional[json.JSONEncoder] = None
    decoder: Optional[json.JSONDecoder] = None
    encoding: str = "utf-8"

    def load(self, **kwargs) -> T:
        if not self.path.exists():
            return {}
        if not kwargs.get("cls"):
            kwargs["cls"] = self.decoder
        with open(self.path, "r", encoding=self.encoding) as json_file:
            content: Dict[str, Any] = json.load(json_file, **kwargs)

        return content

    def write(self, content: Dict[str, Any], **kwargs) -> None:
        if not kwargs:
            kwargs = {"ensure_ascii": False,
                      "indent": 4}
        if not kwargs.get("cls"):
            kwargs["cls"] = self.encoder
        with open(self.path, "w", encoding=self.encoding) as json_file:
            json.dump(content, json_file, **kwargs)
            json_file.write("\n")


class ExtractionEncoder(json.JSONEncoder):
    def default(self, obj: object):
        if isinstance(obj, datetime.datetime):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


class ExtractionDecoder(json.JSONDecoder):
    transformations: Dict[str, Callable[[Any], Any]] = {
        "crawl_date": lambda timestamp: datetime.datetime.fromisoformat(timestamp),
        "publishing_date": lambda timestamp: datetime.datetime.fromisoformat(timestamp),
    }

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj_dict: dict):
        for key, transformation in self.transformations.items():
            if serialized_value := obj_dict.get(key):
                obj_dict[key] = transformation(serialized_value)
        return obj_dict


@dataclass
class JSONFileWithExtractionDecoderEncoder(JSONFile):
    encoder: json.JSONEncoder = ExtractionEncoder
    decoder: json.JSONDecoder = ExtractionDecoder


@dataclass
class HTMLTestFile:
    url: str
    content: str
    crawl_date: datetime.datetime
    publisher: PublisherEnum
    encoding: str = "utf-8"

    @property
    def path(self) -> Path:
        return (
                generate_absolute_section_path(self.publisher)
                / f"{self.publisher.name}_{self.crawl_date.strftime('%Y_%m_%d')}.html.gz"
        )

    @property
    def meta_info(self) -> Dict[str, Any]:
        return get_meta_info_file(self.publisher).load()[self.path.name]

    @staticmethod
    def _parse_path(path: Path) -> PublisherEnum:
        assert path.name.endswith(".html.gz")
        file_name: str = path.name.rsplit(".html.gz")[0]
        publisher_name, date = file_name.split("_", maxsplit=1)
        return PublisherCollection[publisher_name]

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
        publisher = cls._parse_path(path)
        meta_info = get_meta_info_file(publisher).load()[path.name]
        return cls(content=content, publisher=publisher, encoding=encoding, **meta_info)

    def _register_at_meta_info(self):
        meta_info_file = get_meta_info_file(self.publisher)
        meta_info = meta_info_file.load()
        meta_info[self.path.name] = {"url": self.url, "crawl_date": self.crawl_date}
        meta_info_file.write(meta_info, default=str)

    def write(self) -> None:
        with open(self.path, "wb") as file:
            file.write(gzip.compress(bytes(self.content, self.encoding)))
        self._register_at_meta_info()


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


def generate_absolute_section_path(publisher: PublisherEnum) -> Path:
    return test_resource_path / type(publisher).__name__.lower()


def generate_meta_info_path(publisher: PublisherEnum) -> Path:
    return generate_absolute_section_path(publisher) / "meta.info"


def get_meta_info_file(publisher: PublisherEnum) -> JSONFile[Dict[str, Dict[str, str]]]:
    return JSONFileWithExtractionDecoderEncoder(generate_meta_info_path(publisher))


def generate_parser_test_case_json_path(publisher: PublisherEnum) -> Path:
    return generate_absolute_section_path(publisher) / f"{publisher.name}.json"


def load_test_case_data(publisher: PublisherEnum) -> Dict[str, Dict[str, Any]]:
    test_case_json_path = generate_parser_test_case_json_path(publisher)
    test_case_file = JSONFile(test_case_json_path)

    if not (test_data := test_case_file.load()):
        raise ValueError(f"Test case (JSON) for parser '{type(publisher.parser).__name__}' is missing. "
                         f"Use 'python -m scripts.generate_parser_test_files --help' for more information")

    if isinstance(test_data, dict):
        return test_data
    else:
        raise ValueError(
            f"Received invalid JSON format for publisher {repr(publisher.name)}. "
            f"Expected a JSON with a dictionary as root."
        )


def load_supported_publishers_markdown() -> bytes:
    if not supported_publishers_markdown_path.exists():
        raise FileNotFoundError(
            f"The '{supported_publishers_markdown_path.name}' is missing. "
            f"Run 'python -m fundus.utils.generate_tables'"
        )

    with open(supported_publishers_markdown_path, "rb") as file:
        content = file.read()

    return content
