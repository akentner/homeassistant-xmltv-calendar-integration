"""Preview of the programmes a calendar's filters match from now on (pure strings, FLT-10)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .filter import FilterSpec
from .render import to_event_fields

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime, tzinfo

    from .model import EpgData, Programme

PREVIEW_LIMIT = 10

# Fixed tables instead of locale: setlocale is process-global and not thread-safe (A3)
WEEKDAY_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
}


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Number of matches from now on plus the formatted lines of the first ones."""

    count: int
    lines: tuple[str, ...]


def format_line(programme: Programme, channel_name: str, title: str, tz: tzinfo, language: str) -> str:
    """Return `<weekday> <dd.mm.> <HH:MM> · <channel> · <title>` in local time, truncated to the minute (D-17)."""
    local = programme.start.astimezone(tz)
    names = WEEKDAY_NAMES.get(language.split("-", maxsplit=1)[0].lower(), WEEKDAY_NAMES["en"])
    return f"{names[local.weekday()]} {local:%d.%m.} {local:%H:%M} · {channel_name} · {title}"


def build_preview(  # noqa: PLR0913, PLR0917 - positional for async_add_executor_job
    data: Mapping[str, object],
    epg: EpgData,
    now: datetime,
    tz: tzinfo,
    language: str = "en",
    limit: int = PREVIEW_LIMIT,
) -> PreviewResult:
    """Count the calendar's matches with stop > now (airing included, D-16) and format the first `limit`."""
    upcoming = [programme for programme in FilterSpec.from_mapping(data).apply(epg).matches if programme.stop > now]
    lines: list[str] = []
    for programme in upcoming[:limit]:
        channel = epg.channels.get(programme.channel_id)
        channel_name = channel.display_name if channel is not None else programme.channel_id
        title = to_event_fields(programme, channel)["summary"]
        lines.append(format_line(programme, channel_name, title, tz, language))
    return PreviewResult(count=len(upcoming), lines=tuple(lines))
