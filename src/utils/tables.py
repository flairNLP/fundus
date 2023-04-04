import inspect
import os.path
import textwrap
from pathlib import Path
from urllib.parse import urlparse

from doc import docs_path
from src import PublisherCollection


def build_supported_news_table(md_path: str) -> None:
    with open(md_path, "w+", encoding="utf8") as file:
        file.write("# Supported Sources")
        for cc, enum in PublisherCollection.iter_countries():
            file.write(f"\n\n## {cc}")
            head = f"""
            <table class="source {cc}">
                <tr>
                    <th>Source</th>
                    <th>Domain</th>
                    <th>Class</th>
                </tr> """
            file.write(textwrap.dedent(head))
            for publisher in sorted(enum, key=lambda x: x.publisher_name):
                pub_row = f"""
                    <tr>
                        <td>{publisher.publisher_name}</td>
                        <td>
                            <a href="{publisher.domain}">
                                <span>{urlparse(publisher.domain).netloc}</span>
                            </a>
                        </td>
                        <td><code>{publisher.name}</code></td>
                    </tr>"""
                file.write(textwrap.indent(textwrap.dedent(pub_row), prefix="\t"))
            file.write("</table>")


if __name__ == "__main__":
    relative_path = Path("supported_news.md")
    supported_news_path = os.path.join(docs_path, relative_path)

    build_supported_news_table(supported_news_path)

    import subprocess

    process = subprocess.Popen(["git", "add", supported_news_path], stdout=subprocess.PIPE)
