"""Streaming XMLTV parser. Always run it in an executor: it is CPU-bound and may sleep."""

import gzip
import sys
import time
import xml.etree.ElementTree as ET
import zlib
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, BinaryIO

from .model import Channel, EpgData, ParseStats, Programme
from .normalize import normalize_programmes
from .timeparse import parse_xmltv_time

if TYPE_CHECKING:
    from collections.abc import Iterator

GZIP_MAGIC = b"\x1f\x8b"
MAX_DECOMPRESSED_BYTES = 1 << 30  # 1 GiB of (decompressed) XML, gzip-bomb guard (SRC-09)

# Read and decode failures of a hostile or broken feed, translated only around iterparse reads in `_read_events`
# (WR-06). EOFError, BadGzipFile and zlib.error come from truncated or corrupt gzip; Expat raises LookupError for an
# unknown declared encoding and ValueError for multi-byte encoding declarations and decode errors. Their text may
# quote feed content, so it is never kept.
_STREAM_ERRORS = (EOFError, gzip.BadGzipFile, zlib.error, LookupError, ValueError)


class FeedError(Exception):
    """The feed cannot be read as XMLTV. Messages carry positions and class names only, never feed content."""


class FeedTooLargeError(FeedError):
    """The (decompressed) feed exceeds the byte cap."""


class _CappedReader:
    """Binary reader that raises `FeedTooLargeError` once more than `max_bytes` have been read."""

    def __init__(self, raw: BinaryIO, max_bytes: int) -> None:
        self._raw = raw
        self._max_bytes = max_bytes
        self.total = 0

    def read(self, size: int = -1) -> bytes:
        # Never request more than one byte past the cap, so even read(-1) stays bounded
        limit = self._max_bytes - self.total + 1
        data = self._raw.read(limit if size < 0 or size > limit else size)
        self.total += len(data)
        if self.total > self._max_bytes:
            msg = f"feed exceeds {self._max_bytes} bytes"
            raise FeedTooLargeError(msg)
        return data


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


def _read_events(reader: _CappedReader) -> Iterator[tuple[str, ET.Element]]:
    """Yield iterparse events, turning read and decode failures (and only those) into content-free `FeedError`."""
    # Stdlib ElementTree never resolves external entities or DTDs; Expat guards entity amplification
    events = ET.iterparse(reader, events=("start", "end"))  # noqa: S314
    while True:
        try:
            event, elem = next(events)
        except StopIteration:
            return
        except ET.ParseError as err:
            line, column = err.position
            msg = f"invalid XML at line {line}, column {column}"
            raise FeedError(msg) from None
        except _STREAM_ERRORS as err:
            msg = f"unreadable feed: {type(err).__name__} after {reader.total} bytes"
            raise FeedError(msg) from None
        yield event, elem


def _collect(source: _CappedReader, stats: ParseStats, yield_every: int) -> tuple[dict[str, Channel], list[Programme]]:
    """Stream channels and programmes out of the document, skipping and counting malformed programmes."""
    channels: dict[str, Channel] = {}
    programmes: list[Programme] = []
    seen = 0
    events = _read_events(source)
    _, root = next(events)
    for event, elem in events:
        if event != "end":
            continue
        if elem.tag == "programme":
            try:
                programme = _programme(elem)
            except ValueError, OverflowError:
                programme = None  # CR-01: one unconvertible programme is skipped and counted, never fatal
            if programme is None:
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
    return channels, programmes


def parse(
    fileobj: BinaryIO,
    *,
    keep_after: datetime | None = None,
    yield_every: int = 250,
    default_duration: timedelta = timedelta(minutes=60),
    max_bytes: int = MAX_DECOMPRESSED_BYTES,
) -> EpgData:
    """
    Parse a plain or gzip-compressed XMLTV document into `EpgData`. `fileobj` must be seekable.

    Programmes without channel, parsable start or title, and programmes whose conversion raises ValueError or
    OverflowError, are skipped and counted. Programmes whose stop is before `keep_after` are dropped. Every
    `yield_every` programmes the thread sleeps 1 ms so the event loop gets the GIL. Raises `FeedTooLargeError` past
    `max_bytes` of XML and `FeedError` only for read and decode failures; other exceptions propagate unchanged.
    """
    stats = ParseStats()
    # Gzip is detected by its magic bytes only, never by file name or Content-Type (SRC-03)
    head = fileobj.read(2)
    fileobj.seek(0)
    reader = _CappedReader(gzip.GzipFile(fileobj=fileobj) if head == GZIP_MAGIC else fileobj, max_bytes)
    try:
        channels, programmes = _collect(reader, stats, yield_every)
    except StopIteration:
        msg = "empty document"
        raise FeedError(msg) from None

    # Programmes may reference channels without a <channel> element; list them under their ID (EVT-02)
    for programme in programmes:
        if programme.channel_id not in channels:
            channels[programme.channel_id] = Channel(id=programme.channel_id, display_name=programme.channel_id)

    normalized = normalize_programmes(programmes, default_duration=default_duration, stats=stats)
    if keep_after is not None:
        kept = tuple(p for p in normalized if p.stop >= keep_after)
        stats.dropped_past += len(normalized) - len(kept)
        normalized = kept
    stats.programmes = len(normalized)
    stats.channels = len(channels)
    return EpgData(channels=channels, programmes=normalized, stats=stats)
