"""Rendering of programmes into calendar event fields (pure strings)."""

import zlib
from datetime import UTC
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .model import Channel, Programme


class EventFields(TypedDict):
    """Keyword arguments for `CalendarEvent` besides start and end."""

    summary: str
    location: str
    description: str | None
    uid: str


def event_uid(programme: Programme) -> str:
    """Return `<channel_id>-<UTC start %Y%m%dT%H%M%SZ>-<crc32(title) as 8 hex>`, stable across refreshes (EVT-06)."""
    start = programme.start.astimezone(UTC)
    return f"{programme.channel_id}-{start:%Y%m%dT%H%M%SZ}-{zlib.crc32(programme.title.encode()):08x}"


def to_event_fields(programme: Programme, channel: Channel | None) -> EventFields:
    """Return summary `<display-name>: <title>`, location = display name (EVT-02), else the channel id."""
    location = channel.display_name if channel is not None else programme.channel_id
    return EventFields(
        summary=f"{location}: {programme.title}",
        location=location,
        description=programme.description,
        uid=event_uid(programme),
    )
