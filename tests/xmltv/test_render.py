"""Event rendering: stable UIDs (EVT-06)."""

import io
import zlib
from datetime import UTC, datetime, timedelta, timezone

from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.parser import parse
from custom_components.xmltv_calendar.xmltv.render import to_event_fields

CEST = timezone(timedelta(hours=2))
CHANNEL = Channel(id="daserste.de", display_name="Das Erste")

PROGRAMMES = (
    (
        '<programme channel="daserste.de" start="20261013120000 +0200" stop="20261013121500 +0200">'
        "<title>Tagesschau</title></programme>"
    ),
    '<programme channel="daserste.de" start="20261013121500 +0200"><title>Mittagsmagazin</title></programme>',
    '<programme channel="zdf.de" start="20261013120000 +0200"><title>heute</title></programme>',
)


def _feed(programmes: tuple[str, ...]) -> bytes:
    body = "".join(programmes)
    return f'<?xml version="1.0" encoding="UTF-8"?><tv>{body}</tv>'.encode()


def _uids(feed: bytes) -> dict[tuple[str, str], str | None]:
    epg = parse(io.BytesIO(feed), yield_every=0)
    return {(p.channel_id, p.title): to_event_fields(p, None)["uid"] for p in epg.programmes}


def _programme(title: str, start: datetime) -> Programme:
    return Programme(
        channel_id="daserste.de",
        start=start,
        stop=start + timedelta(minutes=15),
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def test_uid_format_and_stability() -> None:
    programme = _programme("Tagesschau", datetime(2026, 10, 13, 12, tzinfo=CEST))
    crc = zlib.crc32(b"Tagesschau")
    assert to_event_fields(programme, CHANNEL)["uid"] == f"daserste.de-20261013T100000Z-{crc:08x}"

    # Two parses of the same bytes, and the same programmes in reversed file order, give identical UIDs
    first = _uids(_feed(PROGRAMMES))
    assert all(isinstance(uid, str) for uid in first.values())
    assert _uids(_feed(PROGRAMMES)) == first
    assert _uids(_feed(PROGRAMMES[::-1])) == first


def test_uid_differs_for_different_titles() -> None:
    start = datetime(2026, 10, 13, 10, tzinfo=UTC)
    uid_a = to_event_fields(_programme("Tagesschau", start), CHANNEL)["uid"]
    uid_b = to_event_fields(_programme("Wetter", start), CHANNEL)["uid"]
    assert uid_a is not None
    assert uid_b is not None
    assert uid_a != uid_b


def test_summary_and_location_unchanged() -> None:
    programme = _programme("Tagesschau", datetime(2026, 10, 13, 10, tzinfo=UTC))
    fields = to_event_fields(programme, CHANNEL)
    assert fields["summary"] == "Das Erste: Tagesschau"
    assert fields["location"] == "Das Erste"
    assert to_event_fields(programme, None)["location"] == "daserste.de"
