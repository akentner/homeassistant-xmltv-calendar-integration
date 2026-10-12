"""Rendering of programmes into calendar event fields (pure strings)."""

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .model import Channel, Programme


class EventFields(TypedDict):
    """Keyword arguments for `CalendarEvent` besides start and end."""

    summary: str
    location: str
    description: str | None
    uid: str | None


def to_event_fields(programme: Programme, channel: Channel | None) -> EventFields:
    """Return summary `<display-name>: <title>`, location = display name (EVT-02), else the channel id."""
    location = channel.display_name if channel is not None else programme.channel_id
    return EventFields(
        summary=f"{location}: {programme.title}",
        location=location,
        description=programme.description,
        uid=None,  # plan 01-02 sets a stable uid
    )
