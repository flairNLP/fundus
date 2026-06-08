from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Dict

from fundus.utils.serialization import JSONVal, serialize_value

__all__ = [
    "HTML",
    "SourceInfo",
]


@dataclass(frozen=True)
class SourceInfo:
    """Provenance metadata for an HTML record.

    The base form carries only the publisher's name; needs to be pickable. Per-backend
    subclasses (WebSourceInfo, WarcSourceInfo) add their own origin fields.

    Attributes:
        publisher (str): The publisher's name (its identity).
    """

    publisher: str

    def serialize(self) -> Dict[str, JSONVal]:
        """Serialize all dataclass fields to a JSON-compatible dict.

        Subclasses inherit this unchanged and automatically pick up their extra fields,
        since it reflects over the dataclass fields rather than naming them explicitly.

        Returns:
            Dict[str, JSONVal]: Field name to JSON-serializable value for every field.
        """
        return {f.name: serialize_value(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class HTML:
    """A fetched HTML document together with its URLs, crawl time, and source provenance.

    The unit of exchange between the Source and Pipeline layers: a Source yields HTML,
    the Pipeline parses it into an Article. Frozen so it can be shared/pickled safely.

    Attributes:
        requested_url (str): The URL that was requested.
        responded_url (str): The final URL after redirects (equals requested_url when none).
        content (str): The decoded HTML body.
        crawl_date (datetime): When the document was fetched (or its WARC record date).
        source_info (SourceInfo): Provenance metadata describing where the record came from.
    """

    requested_url: str
    responded_url: str
    content: str
    crawl_date: datetime
    source_info: SourceInfo

    def serialize(self) -> Dict[str, JSONVal]:
        """Serialize the record to a JSON-compatible dict.

        The crawl date is ISO-formatted and the source info is serialized via its own
        serialize(); all other fields are emitted as-is.

        Returns:
            Dict[str, JSONVal]: The record's fields as JSON-serializable values.
        """
        return {
            "requested_url": self.requested_url,
            "responded_url": self.responded_url,
            "content": self.content,
            "crawl_date": self.crawl_date.isoformat(),
            "source_info": self.source_info.serialize(),
        }
