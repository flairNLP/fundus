import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Union
from urllib.parse import urlparse

from typing_extensions import TypeAlias

from fundus import PublisherCollection
from fundus import __development_base_path__ as root_path
from fundus.publishers.base_objects import PublisherEnum


def generate_line(content: str, indent: int = 0, newline: bool = True) -> str:
    return textwrap.indent(content, prefix="\t" * indent) + ("\n" if newline else "")


ContentT: TypeAlias = Union[str, "Tag"]


@dataclass
class Tag:
    type: str
    content: Union[List[ContentT], ContentT]
    attrs: Dict[str, str] = field(default_factory=dict)
    style: Dict[str, str] = field(default_factory=dict)
    inline: bool = False

    def __str__(self) -> str:
        lines: List[str] = list()
        if self.style:
            inline_style = "; ".join(f"{key}: {value}" for key, value in self.style.items())
            self.attrs.update({"style": inline_style})
        inline_attrs: str = "".join([f' {key}="{value}"' for key, value in self.attrs.items()])
        lines.append(generate_line(f"<{self.type}{inline_attrs}>", newline=not self.inline))
        indent = 1 if not self.inline else 0
        if isinstance(self.content, list):
            lines.extend(generate_line(str(c), indent=indent, newline=False) for c in self.content)
        elif isinstance(self.content, Tag):
            lines.append(generate_line(str(self.content), indent=indent, newline=False))
        elif self.content:
            lines.append(generate_line(str(self.content), indent=indent, newline=not self.inline))
        lines.append(generate_line(f"</{self.type}>"))
        return "".join(lines)


@dataclass
class ColumnFactory:
    content: Callable[[PublisherEnum], Union[List[ContentT], ContentT]]

    def __call__(self, *args, **kwargs) -> Tag:
        return Tag(type="td", content=self.content(*args, **kwargs), inline=False)


max_width: int = 1000
column_mapping: Dict[str, ColumnFactory] = {
    "Source": ColumnFactory(
        content=lambda spec: Tag("div", f"{spec.publisher_name}", style={"text-align": "right"}, inline=True),
    ),
    "Domain": ColumnFactory(
        content=lambda spec: Tag("a", Tag("span", urlparse(spec.domain).netloc, inline=True), {"href": spec.domain})
    ),
    "Validated Attributes": ColumnFactory(
        content=lambda spec: [Tag("code", a, inline=True) for a in spec.parser.attributes().validated.names]
    ),
    "Unvalidated Attributes": ColumnFactory(
        content=lambda spec: [Tag("code", a, inline=True) for a in attrs]
        if (attrs := spec.parser.attributes().unvalidated.names)
        else ""
    ),
    "Class": ColumnFactory(content=lambda spec: Tag("code", spec.name, inline=True)),
}


def generate_thread() -> Tag:
    column_style = {"text-align": "center", "width": f"{max_width // len(column_mapping)}px"}
    ths = [Tag("th", name, inline=True, style=column_style) for name in column_mapping.keys()]
    tr = Tag("tr", ths)
    thread = Tag("thread", tr)
    return thread


def generate_tbody(country: Iterator[PublisherEnum]) -> Tag:
    tbody = Tag("tbody", list())
    for spec in country:
        tds = [column(spec) for column in column_mapping.values()]
        tr = Tag("tr", tds)
        tbody.content.append(tr)
    return tbody


def build_supported_news_svg() -> str:
    md: List[str] = ["# Supported News Tables\n\n"]
    for cc, enum in PublisherCollection.iter_countries():
        md.append(f"\n## {cc.upper()}-News\n")
        table = Tag(
            "table",
            [generate_thread(), generate_tbody(enum)],
            attrs={
                "class": f"source {cc}",
            },
        )
        md.append(str(table))
    return "".join(md)


if __name__ == "__main__":
    md = build_supported_news_svg()

    relative_path = Path("doc/supported_news.md")
    supported_news_path = root_path / relative_path

    with open(supported_news_path, "w+", encoding="utf8") as file:
        file.write(md)

    import subprocess

    process = subprocess.Popen(["git", "add", supported_news_path], stdout=subprocess.PIPE)
