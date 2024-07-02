import itertools
from pathlib import Path
from typing import Dict, Iterable, List, Protocol, Sequence
from urllib.parse import urlparse

import lxml.etree
import lxml.html
import more_itertools
from lxml.html.builder import CLASS, CODE, DIV, SPAN, TABLE, TBODY, TD, TH, THEAD, TR, A

from fundus import PublisherCollection
from fundus import __development_base_path__ as root_path
from fundus.publishers.base_objects import Publisher
from tests.resources import attribute_annotations_mapping

supported_publishers_markdown_path: Path = root_path / "docs" / "supported_publishers.md"


class ColumnFactory(Protocol):
    def __call__(self, publisher: Publisher) -> lxml.html.HtmlElement:
        ...


column_mapping: Dict[str, ColumnFactory] = {
    "Class": lambda publisher: TD(CODE(publisher.__name__)),
    "Name": lambda publisher: TD(DIV(f"{publisher.name}")),
    "URL": lambda publisher: TD(A(SPAN(urlparse(publisher.domain).netloc), href=publisher.domain)),
    "Missing Attributes": lambda publisher: (
        TD(*[CODE(a) for a in sorted(attributes)])
        if (
            attributes := set(attribute_annotations_mapping.keys())
            - set(publisher.parser.latest_version.attributes().validated.names)
        )
        else lxml.html.fromstring("<td>&nbsp;</td>")
    ),
    "Additional Attributes": lambda publisher: (
        TD(*[CODE(a) for a in sorted(attributes)])
        if (attributes := publisher.parser.latest_version.attributes().unvalidated.names)
        else lxml.html.fromstring("<td>&nbsp;</td>")
    ),
}


def generate_thead() -> lxml.html.HtmlElement:
    ths = [TH(name) for name in column_mapping.keys()]
    tr = TR(*ths)
    thead = THEAD(tr)
    return thead


def generate_tbody(country: Iterable[Publisher]) -> lxml.html.HtmlElement:
    content: List[lxml.html.HtmlElement] = []
    for publisher in sorted(country, key=lambda enum: enum.name):
        tds = [column(publisher) for column in column_mapping.values()]
        tr = TR(*tds)
        content.append(tr)
    return TBODY(*content)


def align_tables(tables: Sequence[lxml.html.HtmlElement]) -> None:
    """
    Aligns the columns across the given HTML tables in-place.
    For each column the head text will be padded with non-breaking spaces to the length of longest cell in its column.
    It is required for the tables to have the same number of columns.
    """
    table_heads: List[List[lxml.html.HtmlElement]] = [
        table.xpath("/table/thead/tr/th//text()//parent::*") for table in tables
    ]
    if any(len(head) != len(table_heads[0]) for head in table_heads[1:]):
        raise ValueError("The tables do not have the same number of columns.")

    for column_index, colum_heads in enumerate(
        more_itertools.transpose(table_heads), start=1  # type: ignore[attr-defined]
    ):
        column_texts: List[str] = [
            text for table in tables for text in table.xpath(f"/table/tbody/tr/td[{column_index}]//text()")
        ]
        max_column_length: int = max(len(text) for text in column_texts)

        for head in colum_heads:
            assert head.text is not None
            text: str = head.text.replace(" ", "\u00A0")
            padding: str = "\u00A0" * (2 * (max_column_length - len(head.text)))
            head.text = f"{text}{padding}"


def build_publisher_tables() -> Dict[str, lxml.html.HtmlElement]:
    tables: Dict[str, lxml.html.HtmlElement] = {
        country_code: TABLE(generate_thead(), generate_tbody(enum), CLASS(f"publishers {country_code}"))
        for country_code, enum in sorted(PublisherCollection.get_subgroup_mapping().items())
    }
    align_tables(tuple(tables.values()))
    return tables


def build_supported_publishers_markdown(publisher_tables: Dict[str, lxml.html.HtmlElement]) -> str:
    publisher_sections: List[str] = [
        f"## {country_code.upper()}-Publishers\n\n{lxml.etree.tostring(table, pretty_print=True).decode('utf-8')}"
        for country_code, table in publisher_tables.items()
    ]
    return "\n\n".join(itertools.chain(["# Supported Publishers\n"], publisher_sections))


def main() -> None:
    publisher_tables = build_publisher_tables()
    markdown = build_supported_publishers_markdown(publisher_tables)
    with open(supported_publishers_markdown_path, "w", encoding="utf8") as file:
        file.write(markdown)


if __name__ == "__main__":
    main()
