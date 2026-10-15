"""Event rendering: stable UIDs (EVT-06) and title templates (EVT-03)."""

import io
import zlib
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from custom_components.xmltv_calendar.xmltv.model import Channel, Programme
from custom_components.xmltv_calendar.xmltv.parser import parse
from custom_components.xmltv_calendar.xmltv.render import (
    DEFAULT_TEMPLATES,
    DESCRIPTION_FIELDS,
    INVALID_TEMPLATE,
    TITLE_FIELDS,
    UNKNOWN_PLACEHOLDER,
    EventTemplates,
    TemplateError,
    compile_template,
    to_event_fields,
)

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


# --- Templates (EVT-03, D-20 to D-22) ------------------------------------------------------------------------------

BASIC = Path(__file__).parent.parent / "fixtures" / "basic.xml"
START = datetime(2026, 10, 13, 18, tzinfo=UTC)

R1 = Programme(
    channel_id="daserste.de",
    start=START,
    stop=START + timedelta(minutes=90),
    titles=("Tatort",),
    sub_titles=("Der Fall", "Teil 2"),
    description="Kommissarin ermittelt.",
    categories=("Krimi", "Reihe"),
    episode="1.4.",
)
R2 = _programme("Tagesschau", START)
R3 = Programme(
    channel_id="x.de",
    start=START,
    stop=START + timedelta(minutes=15),
    titles=("Nachrichten",),
    sub_titles=(),
    description=None,
    categories=(),
    episode=None,
)
CHANNELS = {"daserste.de": CHANNEL}


def _title(template: str, programme: Programme) -> str:
    templates = EventTemplates(title=compile_template(template, TITLE_FIELDS))
    return to_event_fields(programme, CHANNELS.get(programme.channel_id), templates)["summary"]


@pytest.mark.parametrize(
    ("template", "programme", "expected"),
    [
        ("{channel}: {title}", R1, "Das Erste: Tatort"),
        ("{channel}: {title}", R3, "x.de: Nachrichten"),
        ("{title} – {subtitle}", R1, "Tatort – Der Fall"),
        ("{title} – {subtitle}", R2, "Tagesschau"),
        ("{title} ({episode})", R1, "Tatort (1.4.)"),
        ("{category}: {title}", R2, "Tagesschau"),
        ("{category}: {title}", R1, "Krimi, Reihe: Tatort"),
        ("{channel_id} | {title}", R1, "daserste.de | Tatort"),
        ("  {title}   {subtitle}  ", R1, "Tatort Der Fall"),
        ("{subtitle}", R2, "Tagesschau"),
        ("{{{title}}}", R1, "{Tatort}"),
    ],
)
def test_title_rendering(template: str, programme: Programme, expected: str) -> None:
    assert _title(template, programme) == expected


@pytest.mark.parametrize(
    ("template", "reason", "detail"),
    [
        ("{foo}", UNKNOWN_PLACEHOLDER, "{foo}"),
        ("{title.__class__}", UNKNOWN_PLACEHOLDER, "{title.__class__}"),
        ("{title[0]}", UNKNOWN_PLACEHOLDER, "{title[0]}"),
        ("{}", UNKNOWN_PLACEHOLDER, "{}"),
        ("{0}", UNKNOWN_PLACEHOLDER, "{0}"),
        ("{title:>9}", UNKNOWN_PLACEHOLDER, "{title}"),
        ("{title!r}", UNKNOWN_PLACEHOLDER, "{title}"),
        ("{title:{channel}}", UNKNOWN_PLACEHOLDER, "{title}"),
        ("{description}", UNKNOWN_PLACEHOLDER, "{description}"),
        ("{title", INVALID_TEMPLATE, None),
        ("title}", INVALID_TEMPLATE, None),
    ],
)
def test_template_error_reasons(template: str, reason: str, detail: str | None) -> None:
    with pytest.raises(TemplateError) as err:
        compile_template(template, TITLE_FIELDS)
    assert err.value.reason == reason
    if detail is not None:
        assert err.value.detail == detail


def test_description_placeholder_allowed_in_description_fields() -> None:
    assert compile_template("{description}", DESCRIPTION_FIELDS) == (("", "description"),)


def test_feed_text_with_braces_renders_literally() -> None:
    # T-02-13: feed values are data, never parsed as a template
    programme = _programme("{channel} {title.__class__}", START)
    assert _title("{title}", programme) == "{channel} {title.__class__}"


def test_uid_ignores_templates() -> None:
    templated = EventTemplates(title=compile_template("{title} – {subtitle}", TITLE_FIELDS))
    assert to_event_fields(R1, CHANNEL, templated)["uid"] == to_event_fields(R1, CHANNEL, DEFAULT_TEMPLATES)["uid"]


def test_default_templates_reproduce_phase1_summary() -> None:
    # Assumption-delta invariant: the default template is the Phase 1 hard-coded summary
    epg = parse(io.BytesIO(BASIC.read_bytes()), yield_every=0)
    cases = [(R1, CHANNEL), (R2, CHANNEL)] + [(p, epg.channels[p.channel_id]) for p in epg.programmes]
    for programme, channel in cases:
        fields = to_event_fields(programme, channel)
        assert fields["summary"] == f"{channel.display_name}: {programme.title}"
        assert fields == to_event_fields(programme, channel, DEFAULT_TEMPLATES)
