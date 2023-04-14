import os.path
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Callable, List, Iterator
from urllib.parse import urlparse

from doc import docs_path
from fundus.publishers import PublisherEnum
from src.fundus import PublisherCollection


@dataclass
class TableColumn:
    content: Callable[[PublisherEnum], str]
    styles: List[str] = field(default_factory=list)

    def __call__(self, *args, **kwargs) -> str:
        style = f' style="{"; ".join(self.styles)}"' if self.styles else ''
        return textwrap.dedent(f'<td{style}>{self.content(*args, **kwargs)}</td>\n')


column_mapping: Dict[str, TableColumn] = {
    "Source": TableColumn(content=lambda spec: f"{spec.publisher_name}", ),
    "Domain": TableColumn(content=lambda spec: (f'\n\t<a href="{spec.domain}">\n'
                                                f'\t\t<span>{urlparse(spec.domain).netloc}</span>\n'
                                                f'\t</a>\n')),
    "Class": TableColumn(content=lambda spec: f"<code>{spec.name}</code>")

}


def generate_style() -> str:
    style: str = f"""
        <style>
            .source {{
                text-align: center;
            }}
            .source td {{
                width: calc(1080px/{len(column_mapping)});
            }}
            .source tr > *:first-of-type {{
                text-align: left;
            }}
            .source tr > *:last-of-type {{
                text-align: right;
            }}
        </style>"""
    return textwrap.dedent(style.strip("\n"))


def generate_thread() -> str:
    thread: List[str] = list()
    thread.append(generate_line("<thread>"))
    thread.append(generate_line("<tr>", indent=+1))
    for key in column_mapping.keys():
        thread.append(generate_line(f"<th>{key}</th>", indent=+2))
    thread.append(generate_line("</tr>", indent=+1))
    thread.append(generate_line("</thread>"))
    return "".join(thread)


def generate_tbody_tr(spec: PublisherEnum) -> str:
    tr: List[str] = list()
    tr.append(generate_line("<tr>"))
    for column in column_mapping.values():
        tr.append(textwrap.indent(column(spec), prefix="\t"))
    tr.append(generate_line("</tr>"))
    return "".join(tr)


def generate_tbody(country: Iterator[PublisherEnum]) -> str:
    tbody: List[str] = list()
    tbody.append(generate_line("<tbody>"))
    for spec in country:
        tbody.append(textwrap.indent(generate_tbody_tr(spec), prefix='\t'))
    tbody.append(generate_line("</tbody>"))
    return "".join(tbody)


def build_supported_news_table() -> str:
    table: List[str] = list()
    table.append(generate_line("# Supported Sources"))
    table.append(generate_style())
    for cc, enum in PublisherCollection.iter_countries():
        table.append(generate_line(f"\n## {cc}"))
        table.append(generate_line(f'<table class="source {cc}">'))
        table.append(textwrap.indent(generate_thread(), prefix="\t"))
        table.append(textwrap.indent(generate_tbody(enum), prefix="\t"))
        table.append(generate_line("</table>"))
    return "".join(table)


def generate_line(content: str, indent: int = 0, newline: bool = True) -> str:
    return "\t" * indent + content + ("\n" if newline else "")


if __name__ == "__main__":
    table = build_supported_news_table()

    relative_path = Path("supported_news.md")
    supported_news_path = os.path.join(docs_path, relative_path)

    with open(supported_news_path, "w+", encoding="utf8") as file:
        file.write(table)

    import subprocess

    process = subprocess.Popen(["git", "add", supported_news_path], stdout=subprocess.PIPE)
