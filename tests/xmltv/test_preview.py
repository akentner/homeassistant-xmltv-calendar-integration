"""Preview: count and lines from now on, edges, local weekday/time format and escaping of feed text (FLT-10)."""

import io
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from custom_components.xmltv_calendar.xmltv.filter import FilterSpec
from custom_components.xmltv_calendar.xmltv.model import Channel, EpgData, ParseStats, Programme
from custom_components.xmltv_calendar.xmltv.parser import parse
from custom_components.xmltv_calendar.xmltv.preview import build_preview, format_line
from custom_components.xmltv_calendar.xmltv.settings import KEY_TIME_FROM, KEY_TIME_TO, KEY_TITLE_TEMPLATE, KEY_WEEKDAYS

TZ = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 10, 13, 10, 0, tzinfo=UTC)  # a Tuesday; 12:00 CEST


def _at(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 10, 13, hour, minute, second, tzinfo=UTC)


def _programme(title: str, start: datetime, stop: datetime, channel_id: str = "ch.de") -> Programme:
    return Programme(
        channel_id=channel_id,
        start=start,
        stop=stop,
        titles=(title,),
        sub_titles=(),
        description=None,
        categories=(),
        episode=None,
    )


def _epg(*programmes: Programme, channels: tuple[Channel, ...] = (Channel("ch.de", "Channel"),)) -> EpgData:
    return EpgData(channels={c.id: c for c in channels}, programmes=programmes, stats=ParseStats())


def _hourly(count: int) -> list[Programme]:
    return [
        _programme(f"P{index}", NOW + timedelta(hours=index), NOW + timedelta(hours=index, minutes=30))
        for index in range(count)
    ]


# --- Count and selection from now on (D-16) ----------------------------------------------------------------------


def test_running_programme_is_counted_and_listed_first() -> None:
    epg = _epg(_programme("Running", _at(9), _at(11)), _programme("Later", _at(12), _at(13)))

    result = build_preview({}, epg, NOW, TZ)

    assert result.count == 2
    assert result.lines[0] == "Tue 13.10. 11:00 · Channel · Channel: Running"
    assert result.lines[1] == "Tue 13.10. 14:00 · Channel · Channel: Later"


def test_programme_ending_now_is_excluded() -> None:
    result = build_preview({}, _epg(_programme("Over", _at(8), _at(10))), NOW, TZ)

    assert result.count == 0
    assert result.lines == ()


def test_programme_starting_now_is_included() -> None:
    result = build_preview({}, _epg(_programme("Starts", _at(10), _at(11))), NOW, TZ)

    assert result.count == 1
    assert result.lines == ("Tue 13.10. 12:00 · Channel · Channel: Starts",)


@pytest.mark.parametrize(
    ("matches", "limit", "count", "lines"),
    [(11, 10, 11, 10), (10, 10, 10, 10), (11, 3, 11, 3)],
    ids=["eleven", "exactly-ten", "limit-3"],
)
def test_count_and_line_limit(matches: int, limit: int, count: int, lines: int) -> None:
    result = build_preview({}, _epg(*_hourly(matches)), NOW, TZ, limit=limit)

    assert result.count == count
    assert len(result.lines) == lines


def test_default_limit_is_ten() -> None:
    result = build_preview({}, _epg(*_hourly(11)), NOW, TZ)

    assert result.count == 11
    assert len(result.lines) == 10


def test_equal_starts_keep_feed_order() -> None:
    channels = (Channel("a.de", "Alpha"), Channel("b.de", "Beta"))
    epg = _epg(
        _programme("Zulu", _at(12), _at(13), channel_id="a.de"),
        _programme("Able", _at(12), _at(13), channel_id="b.de"),
        channels=channels,
    )

    result = build_preview({}, epg, NOW, TZ)

    assert result.lines == (
        "Tue 13.10. 14:00 · Alpha · Alpha: Zulu",
        "Tue 13.10. 14:00 · Beta · Beta: Able",
    )


def test_preview_uses_the_calendar_filter_path() -> None:
    epg = _epg(
        _programme("News", _at(8), _at(9)),
        _programme("News at noon", _at(10), _at(11)),
        _programme("Sports", _at(11), _at(12)),
        _programme("Late news", _at(20), _at(21)),
        _programme("Other", _at(13), _at(14), channel_id="other.de"),
    )
    data = {"channels": ["ch.de"], "include": "news"}

    result = build_preview(data, epg, NOW, TZ)

    expected = [p for p in FilterSpec.from_mapping(data).apply(epg).matches if p.stop > NOW]
    assert [p.title for p in expected] == ["News at noon", "Late news"]
    assert result.count == len(expected)
    assert [line.rsplit(": ", 1)[1] for line in result.lines] == [p.title for p in expected]


def test_missing_channel_shows_its_id() -> None:
    result = build_preview({}, _epg(_programme("Show", _at(12), _at(13), channel_id="x.de")), NOW, TZ)

    assert result.lines == ("Tue 13.10. 14:00 · x.de · x.de: Show",)


# --- Local time format and weekday names (D-17) --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "weekday"),
    [("en", "Tue"), ("de", "Di"), ("de-CH", "Di"), ("DE", "Di"), ("fr", "Tue")],
)
def test_weekday_language(language: str, weekday: str) -> None:
    programme = _programme("Show", _at(10, 0, 59), _at(11))

    assert format_line(programme, "Channel", "Show", TZ, language) == f"{weekday} 13.10. 12:00 · Channel · Show"


def test_time_is_truncated_to_the_minute() -> None:
    programme = _programme("Show", _at(10, 0, 59), _at(11))

    assert format_line(programme, "Channel", "Show", TZ, "en").startswith("Tue 13.10. 12:00 · ")


def test_day_and_month_are_zero_padded_in_winter_time() -> None:
    programme = _programme("Show", datetime(2026, 1, 5, 8, 5, tzinfo=UTC), datetime(2026, 1, 5, 9, tzinfo=UTC))

    assert format_line(programme, "Channel", "Show", TZ, "en") == "Mon 05.01. 09:05 · Channel · Show"


# --- Escaping of untrusted feed text (T-02-05, Pitfall 8) ----------------------------------------------------------


def test_markdown_and_html_in_feed_text_are_escaped() -> None:
    programme = _programme("x", _at(10), _at(11))
    title = "*Live* [Link](javascript:x) _x_ #1 | a & b"

    line = format_line(programme, "<b>Sky</b>", title, TZ, "en")

    assert line == (
        "Tue 13.10. 12:00 · &lt;b&gt;Sky&lt;/b&gt; · \\*Live\\* \\[Link\\](javascript:x) \\_x\\_ \\#1 \\| a &amp; b"
    )


def test_backslash_and_backtick_are_escaped_and_parentheses_kept() -> None:
    programme = _programme("x", _at(10), _at(11))

    line = format_line(programme, "Das Erste", "`code` C:\\path Tagesschau (Das Erste)", TZ, "en")

    assert line == "Tue 13.10. 12:00 · Das Erste · \\`code\\` C:\\\\path Tagesschau (Das Erste)"


# --- Window and weekdays in the given time zone (FLT-09, D-10) -----------------------------------------------------


def test_preview_uses_window_in_given_tz() -> None:
    cest = timezone(timedelta(hours=2))  # the parser's fixed offset for "+0200"

    def berlin(day: int, hour: int) -> datetime:
        return datetime(2026, 10, day, hour, tzinfo=cest)

    epg = _epg(
        _programme("Freitag früh", berlin(16, 1), berlin(16, 1) + timedelta(minutes=30)),
        _programme("Freitag spät", berlin(16, 22), berlin(16, 22) + timedelta(minutes=30)),
        _programme("Samstag Nacht", berlin(17, 1), berlin(17, 1) + timedelta(minutes=30)),
        _programme("Samstag zwei", berlin(17, 2), berlin(17, 2) + timedelta(minutes=30)),
    )
    data = {KEY_TIME_FROM: "22:00", KEY_TIME_TO: "02:00", KEY_WEEKDAYS: ["fri"]}

    result = build_preview(data, epg, datetime(2026, 10, 15, tzinfo=UTC), ZoneInfo("Europe/Berlin"))

    assert result.count == 2
    assert result.lines[0].startswith("Fri 16.10. 22:00")
    assert result.lines[1].startswith("Sat 17.10. 01:00")


# --- Titles through the calendar's templates (D-17) ----------------------------------------------------------------


def test_preview_uses_title_template() -> None:
    feed = (Path(__file__).parent.parent / "fixtures" / "basic.xml").read_bytes()
    epg = parse(io.BytesIO(feed), yield_every=0)

    result = build_preview({KEY_TITLE_TEMPLATE: "{title} – {subtitle}"}, epg, datetime(2026, 10, 13, 6, tzinfo=UTC), TZ)

    assert result.lines[0].endswith("· Das Erste · Formel 1: Großer Preis von Mexiko – Qualifying")
