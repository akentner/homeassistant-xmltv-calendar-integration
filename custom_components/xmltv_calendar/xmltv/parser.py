"""Streaming XMLTV parser. Always run it in an executor: it is CPU-bound and may sleep."""

import gzip
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import BinaryIO

from .model import Channel, EpgData, ParseStats, Programme
from .normalize import normalize_programmes
from .timeparse import parse_xmltv_time

GZIP_MAGIC = b"\x1f\x8b"


class FeedError(Exception):
    """The feed is not well-formed XML."""


def _text(elem: ET.Element) -> str:
    return (elem.text or "").strip()


def _texts(parent: ET.Element, tag: str) -> tuple[str, ...]:
    return tuple(text for child in parent.findall(tag) if (text := _text(child)))


def _first(parent: ET.Element, tag: str) -> str | None:
    texts = _texts(parent, tag)
    return texts[0] if texts else None


def _channel(elem: ET.Element) -> Channel | None:
    channel_id = (elem.get("id") or "").strip()
    if not channel_id:
        return None
    channel_id = sys.intern(channel_id)
    return Channel(id=channel_id, display_name=_first(elem, "display-name") or channel_id)


def _programme(elem: ET.Element) -> Programme | None:
    channel_id = (elem.get("channel") or "").strip()
    start = parse_xmltv_time(elem.get("start"))
    titles = _texts(elem, "title")
    if not channel_id or start is None or not titles:
        return None
    # A missing or unparsable stop is handed to normalize as `stop == start`
    stop = parse_xmltv_time(elem.get("stop")) or start
    return Programme(
        channel_id=sys.intern(channel_id),
        start=start,
        stop=stop,
        titles=titles,
        sub_titles=_texts(elem, "sub-title"),
        description=_first(elem, "desc"),
        categories=_texts(elem, "category"),
        episode=_first(elem, "episode-num"),
    )


def parse(
    fileobj: BinaryIO,
    *,
    keep_after: datetime | None = None,
    yield_every: int = 250,
    default_duration: timedelta = timedelta(minutes=60),
) -> EpgData:
    """
    Parse a plain or gzip-compressed XMLTV document into `EpgData`. `fileobj` must be seekable.

    Programmes without channel, parsable start or title are skipped and counted. Programmes whose stop is before
    `keep_after` are dropped. Every `yield_every` programmes the thread sleeps 1 ms so the event loop gets the GIL.
    """
    stats = ParseStats()
    channels: dict[str, Channel] = {}
    programmes: list[Programme] = []
    seen = 0
    # Gzip is detected by its magic bytes only, never by file name or Content-Type (SRC-03)
    head = fileobj.read(2)
    fileobj.seek(0)
    stream: BinaryIO = gzip.GzipFile(fileobj=fileobj) if head == GZIP_MAGIC else fileobj
    try:
        # Stdlib ElementTree never resolves external entities or DTDs; Expat guards entity amplification
        events = ET.iterparse(stream, events=("start", "end"))  # noqa: S314
        _, root = next(events)
        for event, elem in events:
            if event != "end":
                continue
            if elem.tag == "programme":
                if (programme := _programme(elem)) is None:
                    stats.skipped_malformed += 1
                else:
                    programmes.append(programme)
                root.clear()
                seen += 1
                if yield_every and seen % yield_every == 0:
                    time.sleep(0.001)
            elif elem.tag == "channel":
                if (channel := _channel(elem)) is not None:
                    channels[channel.id] = channel
                root.clear()
    except ET.ParseError as err:
        line, column = err.position
        msg = f"invalid XML at line {line}, column {column}"
        raise FeedError(msg) from None
    except StopIteration:
        msg = "empty document"
        raise FeedError(msg) from None

    normalized = normalize_programmes(programmes, default_duration=default_duration, stats=stats)
    if keep_after is not None:
        kept = tuple(p for p in normalized if p.stop >= keep_after)
        stats.dropped_past += len(normalized) - len(kept)
        normalized = kept
    stats.programmes = len(normalized)
    stats.channels = len(channels)
    return EpgData(channels=channels, programmes=normalized, stats=stats)
