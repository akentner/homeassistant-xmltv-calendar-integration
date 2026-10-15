"""Rendering of programmes into calendar event fields (pure strings)."""

import logging
import re
import string
import zlib
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, TypedDict

from .settings import DEFAULT_TITLE_TEMPLATE, KEY_TITLE_TEMPLATE, with_defaults

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .model import Channel, Programme

_LOGGER = logging.getLogger(__name__)

TITLE_FIELDS = frozenset({"channel", "title", "subtitle", "episode", "category", "channel_id"})  # D-21
DESCRIPTION_FIELDS = TITLE_FIELDS | {"description"}

# TemplateError reasons, also the flow's form error keys
INVALID_TEMPLATE = "invalid_template"
UNKNOWN_PLACEHOLDER = "unknown_placeholder"

type CompiledTemplate = tuple[tuple[str, str | None], ...]

_FORMATTER = string.Formatter()

# Separators left dangling at the edges of a rendered title (D-22, RESEARCH A7)
_SEP = r"[\s\-–—:,;|·/]"
_TITLE_EDGES = re.compile(rf"^{_SEP}+|{_SEP}+$")
_SPACES = re.compile(r"[ \t]{2,}")


class EventFields(TypedDict):
    """Keyword arguments for `CalendarEvent` besides start and end."""

    summary: str
    location: str
    description: str | None
    uid: str


class TemplateError(ValueError):
    """A template that cannot be used; `reason` is a flow error key, `detail` the offending part."""

    def __init__(self, reason: str, detail: str) -> None:
        """Store the flow error key (invalid_template or unknown_placeholder) and the detail."""
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def compile_template(text: str, allowed: frozenset[str]) -> CompiledTemplate:
    """
    Parse a template once into (literal, field | None) pairs, accepting only plain allowed field names.

    Attribute or index access, positional fields, format specs, conversions and nested fields are rejected, so
    nothing in a template can execute at render time (T-02-12, Pitfall 3).
    """
    try:
        pieces = list(_FORMATTER.parse(text))  # parse() is lazy: malformed braces raise while iterating
    except ValueError as err:
        raise TemplateError(INVALID_TEMPLATE, str(err)) from None
    compiled: list[tuple[str, str | None]] = []
    for literal, field, spec, conversion in pieces:
        if field is not None and (field not in allowed or spec or conversion):
            raise TemplateError(UNKNOWN_PLACEHOLDER, "{" + field + "}")
        compiled.append((literal, field))
    return tuple(compiled)


def render_template(compiled: CompiledTemplate, values: Mapping[str, str]) -> str:
    """Join literals and values; values are data and are never parsed as a template (T-02-13)."""
    return "".join(literal + ((values.get(field) or "") if field is not None else "") for literal, field in compiled)


def clean_title(text: str) -> str:
    """Return a rendered title on one line, repeated spaces collapsed, dangling edge separators stripped (D-22)."""
    return _TITLE_EDGES.sub("", _SPACES.sub(" ", text.replace("\n", " ")))


def template_values(programme: Programme, channel: Channel | None) -> dict[str, str]:
    """Return the placeholder values of a programme; missing values are empty strings (D-21, D-22)."""
    return {
        "channel": channel.display_name if channel is not None else programme.channel_id,
        "channel_id": programme.channel_id,
        "title": programme.title,
        "subtitle": programme.sub_titles[0] if programme.sub_titles else "",
        "episode": programme.episode or "",
        "category": ", ".join(programme.categories),
        "description": programme.description or "",
    }


def _stored(text: str, allowed: frozenset[str], default: CompiledTemplate, name: str) -> CompiledTemplate:
    """Compile a stored template; one that does not compile (hand-edited storage) falls back to `default`."""
    try:
        return compile_template(text, allowed)
    except TemplateError:
        _LOGGER.warning("Invalid stored %s template, using the default", name)
        return default


@dataclass(frozen=True, slots=True)
class EventTemplates:
    """The compiled templates of one calendar: shared by the calendar entity and the flow preview (D-17)."""

    title: CompiledTemplate
    description: CompiledTemplate | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> EventTemplates:
        """Build from stored subentry data; never raises."""
        settings = with_defaults(data)
        return cls(title=_stored(settings[KEY_TITLE_TEMPLATE], TITLE_FIELDS, DEFAULT_TEMPLATES.title, "title"))


DEFAULT_TEMPLATES = EventTemplates(title=compile_template(DEFAULT_TITLE_TEMPLATE, TITLE_FIELDS))


def event_uid(programme: Programme) -> str:
    """Return `<channel_id>-<UTC start %Y%m%dT%H%M%SZ>-<crc32(title) as 8 hex>`, stable across refreshes (EVT-06)."""
    # Hashes the raw programme title, never the rendered one, so template edits keep UIDs
    start = programme.start.astimezone(UTC)
    return f"{programme.channel_id}-{start:%Y%m%dT%H%M%SZ}-{zlib.crc32(programme.title.encode()):08x}"


def to_event_fields(
    programme: Programme, channel: Channel | None, templates: EventTemplates = DEFAULT_TEMPLATES
) -> EventFields:
    """Return the templated summary (else the programme title), location = display name else channel ID, and UID."""
    values = template_values(programme, channel)
    return EventFields(
        summary=clean_title(render_template(templates.title, values)) or programme.title,
        location=values["channel"],
        description=programme.description,
        uid=event_uid(programme),
    )
