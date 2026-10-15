"""Parser robustness: gzip by content, bounded decompression, typed errors without content, odd but valid feeds."""

import gzip
import io
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.xmltv_calendar.xmltv import parser
from custom_components.xmltv_calendar.xmltv.model import Channel
from custom_components.xmltv_calendar.xmltv.parser import FeedError, parse

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASIC = (FIXTURES / "basic.xml").read_bytes()
EDGE_CASES = (FIXTURES / "edge_cases.xml").read_bytes()
SENTINEL = "SENTINEL-x9q7"


def _parse(payload: bytes, **kwargs):
    return parse(io.BytesIO(payload), **kwargs)


def _feed(programmes: int) -> bytes:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<tv><channel id="a.de"><display-name>A</display-name></channel>',
    ]
    parts.extend(
        f'<programme channel="a.de" start="20261013{i // 60 % 24:02d}{i % 60:02d}00 +0000">'
        f"<title>P{i}</title></programme>"
        for i in range(programmes)
    )
    parts.append("</tv>")
    return "\n".join(parts).encode()


def _good_plus(bad: str) -> bytes:
    """Return a feed with a valid "Good" programme on a.de followed by the given programme element."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<tv><channel id="a.de"><display-name>A</display-name></channel>'
        '<programme channel="a.de" start="20261013120000 +0000" stop="20261013130000 +0000"><title>Good</title>'
        f"</programme>{bad}</tv>"
    ).encode()


def test_gzip_parses_like_plain() -> None:
    plain = _parse(BASIC)
    compressed = _parse(gzip.compress(BASIC))

    assert compressed.programmes == plain.programmes
    assert dict(compressed.channels) == dict(plain.channels)
    assert len(compressed.programmes) == 4


def test_plain_bytes_named_gz_parse(tmp_path: Path) -> None:
    path = tmp_path / "guide.xml.gz"
    path.write_bytes(BASIC)

    with path.open("rb") as fileobj:
        data = parse(fileobj)

    assert len(data.programmes) == 4


def test_gzip_decompressed_cap() -> None:
    bomb = gzip.compress(b"<tv>" + b" " * 4096 + b"</tv>")
    assert len(bomb) < 1024

    with pytest.raises(FeedError) as excinfo:
        _parse(bomb, max_bytes=1024)

    assert isinstance(excinfo.value, parser.FeedTooLargeError)


def test_plain_input_is_capped_too() -> None:
    with pytest.raises(FeedError) as excinfo:
        _parse(b"<tv>" + b" " * 4096 + b"</tv>", max_bytes=1024)

    assert isinstance(excinfo.value, parser.FeedTooLargeError)


def test_input_within_cap_parses() -> None:
    assert len(_parse(gzip.compress(BASIC), max_bytes=len(BASIC)).programmes) == 4


def test_truncated_gzip_raises_feed_error() -> None:
    payload = gzip.compress(BASIC)

    with pytest.raises(FeedError):
        _parse(payload[: len(payload) // 2])


def test_corrupt_gzip_raises_feed_error() -> None:
    with pytest.raises(FeedError):
        _parse(b"\x1f\x8b" + b"not a deflate stream")


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"not xml", id="not-xml"),
        pytest.param(BASIC[: len(BASIC) // 2], id="truncated-xml"),
    ],
)
def test_broken_input_raises_feed_error(payload: bytes) -> None:
    with pytest.raises(FeedError):
        _parse(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(f'<?xml version="1.0" encoding="{SENTINEL}"?><tv></tv>'.encode(), id="unknown-encoding"),
        pytest.param(f"<tv><programme>{SENTINEL} &nbsp; </programme></tv>".encode(), id="undefined-entity"),
        pytest.param(f"<tv><title>{SENTINEL}</title>".encode(), id="truncated"),
        pytest.param(gzip.compress(f"<tv><title>{SENTINEL}</title></tv>".encode())[:20], id="truncated-gzip"),
    ],
)
def test_error_message_has_no_feed_content(payload: bytes) -> None:
    with pytest.raises(FeedError) as excinfo:
        _parse(payload)

    assert SENTINEL not in str(excinfo.value)
    assert excinfo.value.__cause__ is None


def test_display_name_fallback() -> None:
    data = _parse(EDGE_CASES)

    assert data.channels["nodisplay.de"] == Channel("nodisplay.de", "nodisplay.de")
    assert data.channels["daserste.de"].display_name == "Das Erste"


def test_programme_only_channel_is_listed() -> None:
    data = _parse(EDGE_CASES)

    assert data.channels.get("orphan.de") == Channel("orphan.de", "orphan.de")
    assert [p.title for p in data.programmes if p.channel_id == "orphan.de"] == ["Waisenkanal"]
    assert data.stats.channels == 3


def test_skips_malformed_programmes() -> None:
    data = _parse(EDGE_CASES)

    assert data.stats.skipped_malformed == 3
    assert sorted(p.title for p in data.programmes) == ["Großer Preis", "Ohne Anzeigenamen", "Waisenkanal"]


def test_umlaut_title_preserved() -> None:
    data = _parse(EDGE_CASES)

    assert "Großer Preis" in {p.title for p in data.programmes}


def test_latin1_declared_encoding() -> None:
    raw = (FIXTURES / "latin1.xml").read_bytes()
    assert "Ö".encode("iso-8859-1") in raw

    data = _parse(raw)

    assert data.channels["daserste.de"].display_name == "Das Erste Ö"
    assert [p.title for p in data.programmes] == ["Straße"]


@pytest.mark.parametrize(("yield_every", "sleeps"), [(250, 4), (0, 0)])
def test_yield_every_calls_sleep(monkeypatch: pytest.MonkeyPatch, yield_every: int, sleeps: int) -> None:
    calls: list[float] = []
    monkeypatch.setattr(parser, "time", SimpleNamespace(sleep=calls.append))

    data = _parse(_feed(1000), yield_every=yield_every)

    assert len(data.programmes) == 1000
    assert len(calls) == sleeps


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param('start="20261013140000 +2500"', id="offset-plus-2500"),
        pytest.param('start="20261013140000 -2500"', id="offset-minus-2500"),
        pytest.param('start="20261013140000 +0099"', id="offset-minutes-99"),
        pytest.param('start="00010101000000 +0100"', id="year-0001"),
        pytest.param('start="99991231233000 -0100" stop="99991231235959 -0100"', id="year-9999-with-stop"),
        pytest.param('start="99991231233000 +0000"', id="year-9999-without-stop"),
    ],
)
def test_malformed_timestamp_skips_only_that_programme(bad: str) -> None:
    data = _parse(_good_plus(f'<programme channel="a.de" {bad}><title>Bad</title></programme>'))

    assert [p.title for p in data.programmes] == ["Good"]
    assert data.stats.skipped_malformed == 1


def test_unparsable_stop_offset_infers_stop() -> None:
    data = _parse(
        _good_plus(
            '<programme channel="a.de" start="20261013140000 +0000" stop="20261013150000 +2500">'
            "<title>Broken stop</title></programme>"
        )
    )

    assert [p.title for p in data.programmes] == ["Good", "Broken stop"]
    assert data.programmes[1].stop == datetime(2026, 10, 13, 15, tzinfo=UTC)  # start + 60 min default (D-12)
    assert data.stats.inferred_stops == 1
    assert data.stats.skipped_malformed == 0


BAD_START = "20261013140000 +0000"


@pytest.mark.parametrize("error", [ValueError, OverflowError])
def test_conversion_error_skips_only_that_programme(monkeypatch: pytest.MonkeyPatch, error: type[Exception]) -> None:
    real = parser.parse_xmltv_time

    def flaky(value: str | None):
        if value == BAD_START:
            msg = "boom"
            raise error(msg)
        return real(value)

    monkeypatch.setattr(parser, "parse_xmltv_time", flaky)

    data = _parse(_good_plus(f'<programme channel="a.de" start="{BAD_START}"><title>Bad</title></programme>'))

    assert [p.title for p in data.programmes] == ["Good"]
    assert data.stats.skipped_malformed == 1


def test_programming_error_is_not_reported_as_feed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(elem):
        msg = "bug"
        raise KeyError(msg)

    monkeypatch.setattr(parser, "_programme", broken)

    with pytest.raises(KeyError):
        _parse(_good_plus(f'<programme channel="a.de" start="{BAD_START}"><title>Bad</title></programme>'))


def test_multibyte_encoding_declaration_raises_feed_error() -> None:
    with pytest.raises(FeedError) as excinfo:
        _parse(b'<?xml version="1.0" encoding="Shift_JIS"?><tv></tv>')

    assert excinfo.value.__cause__ is None


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def test_text_is_nfc_and_ids_are_untouched() -> None:
    channel_id = _nfd("café.de")
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<tv><channel id="{channel_id}"><display-name>{_nfd("Café Fernsehen")}</display-name></channel>'
        f'<programme channel="{channel_id}" start="20261013120000 +0000" stop="20261013130000 +0000">'
        f"<title>{_nfd('Tatort Köln')}</title><sub-title>{_nfd('Der Löwe')}</sub-title>"
        f"<desc>{_nfd('Schöne Grüße')}</desc><category>{_nfd('Krimi für Ältere')}</category>"
        f"<episode-num>{_nfd('Folge ü1')}</episode-num></programme></tv>"
    ).encode()

    data = _parse(feed)

    (programme,) = data.programmes
    texts = (
        *programme.titles,
        *programme.sub_titles,
        programme.description,
        *programme.categories,
        programme.episode,
        data.channels[channel_id].display_name,
    )
    assert texts == ("Tatort Köln", "Der Löwe", "Schöne Grüße", "Krimi für Ältere", "Folge ü1", "Café Fernsehen")
    assert all(unicodedata.is_normalized("NFC", text) for text in texts)
    # Channel IDs are identifiers, never normalized
    assert programme.channel_id.encode() == channel_id.encode()
    assert list(data.channels) == [channel_id]
