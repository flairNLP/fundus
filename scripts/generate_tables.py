from typing import Dict, Iterator, List, Protocol
from urllib.parse import urlparse

import lxml.etree
import lxml.html
from lxml.html.builder import DIV, A, SPAN, CODE, TH, TR, THEAD, TBODY, TABLE, CLASS, TD

from fundus import PublisherCollection
from fundus import __development_base_path__ as root_path
from fundus.publishers.base_objects import PublisherEnum
from tests.resources import attribute_annotations_mapping

supported_publishers_markdown_path = root_path / "docs" / "supported_publishers.md"


class ColumnFactory(Protocol):
    def __call__(self, spec: PublisherEnum) -> lxml.html.HtmlElement:
        ...


column_mapping: Dict[str, ColumnFactory] = {
    "Source": lambda spec: DIV(f"{spec.publisher_name}"),
    "Domain": lambda spec: A(SPAN(urlparse(spec.domain).netloc), href=spec.domain),
    "Missing Attributes": lambda spec: DIV(*[CODE(a) for a in attributes])
    if (
        attributes := set(attribute_annotations_mapping.keys())
                      - set(spec.parser.latest_version.attributes().validated.names)
    )
    else "",
    "Additional Attributes": lambda spec: DIV(*[CODE(a) for a in attributes])
    if (attributes := spec.parser.latest_version.attributes().unvalidated.names)
    else "",
    "Class": lambda spec: CODE(spec.name),
}


def generate_thread() -> lxml.html.HtmlElement:
    ths = [TH(name) for name in column_mapping.keys()]
    tr = TR(*ths)
    thead = THEAD(tr)
    return thead


def generate_tbody(country: Iterator[PublisherEnum]) -> lxml.html.HtmlElement:
    content: List[lxml.html.HtmlElement] = list()
    for spec in country:
        tds = [TD(column(spec)) for column in column_mapping.values()]
        tr = TR(*tds)
        content.append(tr)
    return TBODY(*content)


def build_supported_publisher_markdown() -> str:
    markdown_pieces: List[str] = ["# Supported News Tables\n\n"]
    for country_code, enum in PublisherCollection.iter_enums():
        markdown_pieces.append(f"\n## {country_code.upper()}-Publishers\n")
        table = TABLE(generate_thread(), generate_tbody(enum), CLASS(f"publishers {country_code}"))
        markdown_pieces.append(lxml.etree.tostring(table, pretty_print=True).decode("utf-8"))
    return "".join(markdown_pieces)


if __name__ == "__main__":
    markdown = build_supported_publisher_markdown()

    with open(supported_publishers_markdown_path, "w", encoding="utf8") as file:
        file.write(markdown)

    import subprocess

    process = subprocess.Popen(["git", "add", supported_publishers_markdown_path], stdout=subprocess.PIPE)
