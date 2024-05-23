import datetime
import gzip
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from typing_extensions import Self

from fundus import PublisherCollection
from fundus.parser import ArticleBody, BaseParser
from fundus.parser.data import TextSequenceTree
from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.html import HTML, SourceInfo
from scripts.generate_tables import supported_publishers_markdown_path
from tests.resources.parser.test_data import __module_path__ as test_resource_path

_T = TypeVar("_T")


def get_test_articles(publisher: Publisher) -> List[Article]:
    articles = []
    html_mapping = load_html_test_file_mapping(publisher)
    for html_test_file in html_mapping.values():
        extraction = publisher.parser(html_test_file.crawl_date).parse(html_test_file.content)
        html = HTML(
            content=html_test_file.content,
            crawl_date=html_test_file.crawl_date,
            requested_url=html_test_file.url,
            responded_url=html_test_file.url,
            source_info=SourceInfo(publisher.name),
        )
        article = Article.from_extracted(extracted=extraction, html=html)
        articles.append(article)
    return articles


@dataclass
class JSONFile(Generic[_T]):
    """Generic file class representing a JSON file.

    You can specify custom json.JSONEncoder/json.JSONDecoder and type hint
    expected JSON structure.

    Example:
        >>> class CustomEncoder(json.JSONEncoder): ...
        >>> class CustomDecoder(json.JSONDecoder): ...
        >>> path_to_json = Path("path/to.json")
        >>> json_file: JSONFile[Dict[str, list]] = JSONFile(path_to_json, encoder=CustomEncoder, decoder=CustomDecoder)
        >>> content = json_file.load() # will type hint content as Dict[str, list]
        >>> content["entry"].append("new")
        >>> json_file.write(content)
    """

    path: Path
    encoder: Optional[Type[json.JSONEncoder]] = None
    decoder: Optional[Type[json.JSONDecoder]] = None
    encoding: str = "utf-8"

    def load(self, **kwargs) -> Optional[_T]:
        """Load file content using json.load().

        See the documentation of json.load() for further documentation
        about the keyword arguments (**kwargs).
        https://docs.python.org/3/library/json.html#json.load


        Args:
            **kwargs: Key word arguments for json.load()

        Returns:
            File content as if loaded with json.load(). If JSONFile is type hinted
                properly, the expected return type is _T.
        """
        if not self.path.exists():
            return None
        if not kwargs.get("cls"):
            kwargs["cls"] = self.decoder
        with open(self.path, "r", encoding=self.encoding) as json_file:
            content: _T = json.load(json_file, **kwargs)
        return content

    def write(self, content: _T, **kwargs) -> None:
        """Writes the given content to the file with json.dump()

        See the documentation of json.dump() for further documentation
        about the keyword arguments (**kwargs).
        https://docs.python.org/3/library/json.html#json.dump

        Args:
            content: The content to write to the file.
            **kwargs: Keyword arguments for json.dump(), Defaults to {"ensure_ascii": False, "indent": 2}

        Returns:

        """
        if not kwargs:
            kwargs = {"ensure_ascii": False, "indent": 2}
        if not kwargs.get("cls"):
            kwargs["cls"] = self.encoder
        with open(self.path, "w", encoding=self.encoding) as json_file:
            json.dump(content, json_file, **kwargs)
            json_file.write("\n")

        subprocess.call(["git", "add", self.path], stdout=subprocess.PIPE)


class ExtractionEncoder(json.JSONEncoder):
    def default(self, obj: object):
        if isinstance(obj, datetime.datetime):
            return str(obj)
        if isinstance(obj, TextSequenceTree):
            return obj.serialize()
        return json.JSONEncoder.default(self, obj)


class ExtractionDecoder(json.JSONDecoder):
    deserialization_functions: Dict[str, Callable[[Any], Any]] = {
        "crawl_date": datetime.datetime.fromisoformat,
        "publishing_date": datetime.datetime.fromisoformat,
        "body": ArticleBody.deserialize,
    }

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj_dict):
        for key, deserialization_function in self.deserialization_functions.items():
            if (serialized_value := obj_dict.get(key)) is not None:
                obj_dict[key] = deserialization_function(serialized_value)
        return obj_dict


@dataclass
class JSONFileWithExtractionDecoderEncoder(JSONFile[_T]):
    """Custom JSONFile using default ExtractionEncoder/ExtractionDecoder"""

    encoder: Type[json.JSONEncoder] = ExtractionEncoder
    decoder: Type[json.JSONDecoder] = ExtractionDecoder


@dataclass
class HTMLTestFile:
    """Utility class representing an HTML test case file with meta infos attached.

    When used with default constructor, writing the file will automatically generate
    a file name and path where to write the content and register meta information about
    the file to the corresponding meta.info file.

    When used with alternative constructor HTMLTestFile.load(), the meta information will
    be read the info file automatically.
    """

    url: str
    content: str
    crawl_date: datetime.datetime
    publisher: Publisher
    encoding: str = "utf-8"

    @property
    def path(self) -> Path:
        return (
            generate_absolute_section_path(self.publisher)
            / f"{self.publisher.name}_{self.crawl_date.strftime('%Y_%m_%d')}.html.gz"
        )

    @property
    def meta_info(self) -> Optional[Dict[str, Any]]:
        if meta_info := get_meta_info_file(self.publisher).load():
            return meta_info[self.path.name]
        return None

    @staticmethod
    def _parse_path(path: Path) -> Publisher:
        assert path.name.endswith(".html.gz")
        file_name: str = path.name.rsplit(".html.gz")[0]
        publisher_name, date = file_name.split("_", maxsplit=1)
        return PublisherCollection[publisher_name]

    @classmethod
    def load(cls, path: Path, encoding: str = "utf-8") -> Self:
        """Loads an HTMLTestFile from the given path.

        See write() for more information about the path syntax.

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
        if not (meta_info := get_meta_info_file(publisher).load()):
            raise ValueError(f"Missing meta info for file {path.name!r}")
        return cls(content=content, publisher=publisher, encoding=encoding, **meta_info[path.name])

    def _register_at_meta_info(self) -> None:
        """Writes meta information about the file to the corresponding meta.info file.

        Returns:
            None
        """
        meta_info_file = get_meta_info_file(self.publisher)
        meta_info = meta_info_file.load() or {}
        meta_info[self.path.name] = {"url": self.url, "crawl_date": self.crawl_date}
        meta_info = dict(sorted(meta_info.items()))
        meta_info_file.write(meta_info)

    def write(self) -> None:
        """Writes the test file to an autogenerated path.

        This function writes self.content to an autogenerated path and registers additional
        meta information about the test file to the corresponding meta.info file.

        You can find the corresponding meta.info file under::

            test_resource_path / <country_code> / meta.info

        The file path syntax is defined as following::

            test_resource_path / <country_code> / <publisher_name>_<year>_<month>_<day>.html.gz

        with:
            | <country_code>: 2-letter code, e.g. us for United States were the publisher originates
            | <publisher_name>: the enum name, e.g. DW, FAZ, APNews
            | <year>_<month>_<day>: parsed date object, as when using date.strftime('%Y_%m_%d')

        Returns:
            None

        """

        # ensure that path exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "wb") as file:
            file.write(gzip.compress(bytes(self.content, self.encoding)))
        self._register_at_meta_info()


def load_html_test_file_mapping(publisher: Publisher) -> Dict[Type[BaseParser], HTMLTestFile]:
    html_paths = (test_resource_path / Path(f"{publisher.contained_in}")).glob(f"{publisher.referenced_name}*.html.gz")
    html_files = [HTMLTestFile.load(path) for path in html_paths]
    html_mapping: Dict[Type[BaseParser], HTMLTestFile] = {}
    for html_file in html_files:
        versioned_parser = publisher.parser(html_file.crawl_date)
        if html_mapping.get(type(versioned_parser)):
            raise KeyError(f"Duplicate html files for {publisher.name!r} and version {type(versioned_parser).__name__}")
        html_mapping[type(versioned_parser)] = html_file
    return html_mapping


def generate_absolute_section_path(publisher: Publisher) -> Path:
    return test_resource_path / publisher.contained_in


def generate_meta_info_path(publisher: Publisher) -> Path:
    return generate_absolute_section_path(publisher) / "meta.info"


def get_meta_info_file(publisher: Publisher) -> JSONFile[Dict[str, Dict[str, Any]]]:
    return JSONFileWithExtractionDecoderEncoder(generate_meta_info_path(publisher))


def generate_parser_test_case_json_path(publisher: Publisher) -> Path:
    return generate_absolute_section_path(publisher) / f"{publisher.referenced_name}.json"


def get_test_case_json(publisher: Publisher) -> JSONFile[Dict[str, Dict[str, Any]]]:
    return JSONFileWithExtractionDecoderEncoder(generate_parser_test_case_json_path(publisher))


def load_test_case_data(publisher: Publisher) -> Dict[str, Dict[str, Any]]:
    test_case_file = get_test_case_json(publisher)

    if not (test_data := test_case_file.load()):
        raise ValueError(
            f"Test case (JSON) for parser {type(publisher.parser).__name__!r} is missing. "
            f"Use 'python -m scripts.generate_parser_test_files --help' for more information"
        )

    if isinstance(test_data, dict):
        return test_data
    else:
        raise ValueError(
            f"Received invalid JSON format for publisher {publisher.name!r}. "
            f"Expected a JSON with a dictionary as root."
        )


def load_supported_publishers_markdown() -> bytes:
    if not supported_publishers_markdown_path.exists():
        raise FileNotFoundError(
            f"The {supported_publishers_markdown_path.name!r} is missing. "
            f"Run 'python -m fundus.utils.generate_tables'"
        )

    with open(supported_publishers_markdown_path, "rb") as file:
        content = file.read()

    return content
