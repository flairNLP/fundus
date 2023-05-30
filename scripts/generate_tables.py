from typing import Dict, Iterable, List, Protocol, cast
from urllib.parse import urlparse

import lxml.etree
import lxml.html
from lxml.html.builder import CLASS, CODE, DIV, SPAN, TABLE, TBODY, TD, TH, THEAD, TR, A

from fundus import PublisherCollection
from fundus import __development_base_path__ as root_path
from fundus.publishers.base_objects import PublisherEnum
from tests.resources import attribute_annotations_mapping

supported_publishers_markdown_path = root_path / "docs" / "supported_publishers.md"


class ColumnFactory(Protocol):
    def __call__(self, spec: PublisherEnum) -> lxml.html.HtmlElement:
        ...


column_mapping: Dict[str, ColumnFactory] = {
    "Source": lambda spec: TD(DIV(f"{spec.publisher_name}")),
    "Domain": lambda spec: TD(A(SPAN(urlparse(spec.domain).netloc), href=spec.domain)),
    "Missing Attributes": lambda spec: TD(*[CODE(a) for a in sorted(attributes)])
    if (
        attributes := set(attribute_annotations_mapping.keys())
        - set(spec.parser.latest_version.attributes().validated.names)
    )
    else cast(lxml.html.HtmlElement, lxml.html.fromstring("<td>&nbsp;</td>")),
    "Additional Attributes": lambda spec: TD(*[CODE(a) for a in sorted(attributes)])
    if (attributes := spec.parser.latest_version.attributes().unvalidated.names)
    else cast(lxml.html.HtmlElement, lxml.html.fromstring("<td>&nbsp;</td>")),
    "Class": lambda spec: TD(CODE(spec.name)),
}


def generate_thread() -> lxml.html.HtmlElement:
    ths = [TH(name) for name in column_mapping.keys()]
    tr = TR(*ths)
    thead = THEAD(tr)
    return thead


def generate_tbody(country: Iterable[PublisherEnum]) -> lxml.html.HtmlElement:
    content: List[lxml.html.HtmlElement] = []
    for spec in sorted(country, key=lambda enum: enum.publisher_name):
        tds = [column(spec) for column in column_mapping.values()]
        tr = TR(*tds)
        content.append(tr)
    return TBODY(*content)


def build_supported_publisher_markdown() -> str:
    markdown_pieces: List[str] = ["# Supported Publishers\n\n"]
    for country_code, enum in sorted(PublisherCollection.get_publisher_enum_mapping().items()):
        markdown_pieces.append(f"\n## {country_code.upper()}-Publishers\n")
        table = TABLE(generate_thread(), generate_tbody(enum), CLASS(f"publishers {country_code}"))
        markdown_pieces.append(lxml.etree.tostring(table, pretty_print=True).decode("utf-8"))
    return "".join(markdown_pieces)


if __name__ == "__main__":
    markdown = build_supported_publisher_markdown()

    with open(supported_publishers_markdown_path, "w", encoding="utf8") as file:
        file.write(markdown)
