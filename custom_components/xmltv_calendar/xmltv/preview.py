"""Preview of the programmes a calendar's filters match from now on (pure strings, FLT-10)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .filter import FilterSpec
from .render import EventTemplates, to_event_fields

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime, tzinfo

    from .model import EpgData, Programme

PREVIEW_LIMIT = 10

# Fixed tables instead of the process locale, which is global and not thread-safe (A3)
WEEKDAY_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
}


# The menu description is rendered as Markdown with HTML: neutralise entities first, then Markdown syntax.
# Backslash comes first so the added escapes are not escaped again; parentheses stay readable (no [ ] -> no link).
_HTML_ESCAPES = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))
_MARKDOWN_CHARS = ("\\", "`", "*", "_", "[", "]", "#", "|")


def escape_markdown(text: str) -> str:
    """Return feed text that renders literally in a Markdown/HTML description (T-02-05, Pitfall 8)."""
    for char, entity in _HTML_ESCAPES:
        text = text.replace(char, entity)
    for char in _MARKDOWN_CHARS:
        text = text.replace(char, f"\\{char}")
    return text


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Number of matches from now on plus the formatted lines of the first ones."""

    count: int
    lines: tuple[str, ...]


def format_line(programme: Programme, channel_name: str, title: str, tz: tzinfo, language: str) -> str:
    """Return `<weekday> <dd.mm.> <HH:MM> · <channel> · <title>` in local time, truncated to the minute (D-17)."""
    local = programme.start.astimezone(tz)
    # Primary language subtag ("de-CH" -> "de"); unknown languages fall back to English
    names = WEEKDAY_NAMES.get(language.split("-", maxsplit=1)[0].lower(), WEEKDAY_NAMES["en"])
    # strftime truncates the seconds, never rounds; only feed text is escaped, the date and time parts are generated
    stamp = f"{names[local.weekday()]} {local:%d.%m.} {local:%H:%M}"
    return f"{stamp} · {escape_markdown(channel_name)} · {escape_markdown(title)}"


def build_preview(  # noqa: PLR0913, PLR0917 - positional for async_add_executor_job
    data: Mapping[str, object],
    epg: EpgData,
    now: datetime,
    tz: tzinfo,
    language: str = "en",
    limit: int = PREVIEW_LIMIT,
) -> PreviewResult:
    """Count the calendar's matches with stop > now (airing included, D-16) and format the first `limit`."""
    # Same filter and time zone as the calendar entity, so the preview shows what the calendar will show
    matches = FilterSpec.from_mapping(data).apply(epg, tz=tz).matches
    templates = EventTemplates.from_mapping(data)  # same title rendering as the entity (D-17)
    upcoming = [programme for programme in matches if programme.stop > now]
    lines: list[str] = []
    for programme in upcoming[:limit]:
        channel = epg.channels.get(programme.channel_id)
        channel_name = channel.display_name if channel is not None else programme.channel_id
        title = to_event_fields(programme, channel, templates)["summary"]
        lines.append(format_line(programme, channel_name, title, tz, language))
    return PreviewResult(count=len(upcoming), lines=tuple(lines))
