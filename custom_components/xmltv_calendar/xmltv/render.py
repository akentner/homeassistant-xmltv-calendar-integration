"""Rendering of programmes into calendar event fields (pure strings)."""

import logging
import re
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypedDict

from .model import Channel, Programme
from .settings import DEFAULT_TITLE_TEMPLATE, KEY_DESCRIPTION_TEMPLATE, KEY_TITLE_TEMPLATE, with_defaults
from .template_engine import (
    INVALID_TEMPLATE,
    LEGACY_PLACEHOLDER,
    MAX_DESCRIPTION_TEMPLATE_LENGTH,
    MAX_TITLE_TEMPLATE_LENGTH,
    TEMPLATE_ERROR_REASONS,
    TEMPLATE_RUNTIME_ERROR,
    UNKNOWN_FILTER,
    UNKNOWN_PLACEHOLDER,
    UNSUPPORTED_SYNTAX,
    VARIABLE_ORDER,
    VARIABLES,
    TemplateError,
    compile_template,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import tzinfo

    from jinja2 import Template

__all__ = [
    "DEFAULT_TEMPLATES",
    "INVALID_TEMPLATE",
    "LEGACY_PLACEHOLDER",
    "MAX_DESCRIPTION_TEMPLATE_LENGTH",
    "MAX_TITLE_TEMPLATE_LENGTH",
    "TEMPLATE_ERROR_REASONS",
    "TEMPLATE_RUNTIME_ERROR",
    "UNKNOWN_FILTER",
    "UNKNOWN_PLACEHOLDER",
    "UNSUPPORTED_SYNTAX",
    "VARIABLES",
    "VARIABLE_ORDER",
    "EventFields",
    "EventTemplates",
    "TemplateError",
    "clean_description",
    "clean_title",
    "compile_template",
    "default_description",
    "event_uid",
    "template_values",
    "to_event_fields",
    "validate_template",
]

_LOGGER = logging.getLogger(__name__)

# Separators left dangling at the edges of a rendered title (D-22, RESEARCH A7)
_SEP = r"[\s\-–—:,;|·/]"
_TITLE_EDGES = re.compile(rf"^{_SEP}+|{_SEP}+$")
_SPACES = re.compile(r"[ \t]{2,}")
# Descriptions are cleaned as a whole, never per line (Pitfall 9). A dash or "·" at the very start is kept as a
# bullet ("- {{ subtitle }}"); other dangling punctuation at the start and any separators at the end are stripped
_DESCRIPTION_START = re.compile(r"^[\s:,;|/]+")
_DESCRIPTION_END = re.compile(rf"{_SEP}+$")
_BLANK_LINES = re.compile(r"\n{3,}")


class EventFields(TypedDict):
    """Keyword arguments for `CalendarEvent` besides start and end."""

    summary: str
    location: str
    description: str | None
    uid: str


def clean_title(text: str) -> str:
    """Return a rendered title on one line, repeated spaces collapsed, dangling edge separators stripped (D-22)."""
    return _TITLE_EDGES.sub("", _SPACES.sub(" ", text.replace("\n", " ")))


def clean_description(text: str) -> str | None:
    """Return a rendered description with line breaks kept: spaces collapsed, at most one blank line, edges stripped."""
    text = _BLANK_LINES.sub("\n\n", _SPACES.sub(" ", text))
    return _DESCRIPTION_END.sub("", _DESCRIPTION_START.sub("", text)) or None


def default_description(programme: Programme) -> str | None:
    """
    Return the D-23 description: sub-title, episode and categories lines, a blank line, then the feed description.

    Lines without data are dropped with their label; None when nothing is left. Labels are English (D-23).
    """
    lines = (
        programme.sub_titles[0] if programme.sub_titles else "",
        f"Episode: {programme.episode}" if programme.episode else "",
        f"Categories: {', '.join(programme.categories)}" if programme.categories else "",
    )
    head = "\n".join(line for line in lines if line)
    return "\n\n".join(part for part in (head, programme.description or "") if part) or None


# Synthetic programmes for the trial render of the flow validation: one fully populated, one with every optional field
# empty. Synthetic by design, so an error detail never carries feed content (T-05-08)
_SAMPLE_CHANNEL = Channel(id="sample.example", display_name="Sample Channel")
SAMPLE_FULL = Programme(
    channel_id="sample.example",
    start=datetime(2026, 1, 15, 20, 15, tzinfo=UTC),
    stop=datetime(2026, 1, 15, 21, 45, tzinfo=UTC),
    titles=("Sample Title", "Sample Original Title"),
    sub_titles=("Sample Subtitle", "Sample Second Subtitle"),
    description="First description line.\nSecond description line.",
    categories=("Sport", "Motorsport"),
    episode="S2024E05",
)
SAMPLE_SPARSE = Programme(
    channel_id="sample.example",
    start=datetime(2026, 1, 15, 20, 15, tzinfo=UTC),
    stop=datetime(2026, 1, 15, 21, 45, tzinfo=UTC),
    titles=("Sample Title",),
    sub_titles=(),
    description=None,
    categories=(),
    episode=None,
)
_MAX_RUNTIME_DETAIL = 200


def validate_template(text: str, *, description: bool = False) -> None:
    """
    Raise a TemplateError when `text` is not a usable title (or description) template; the flow's validation.

    After a successful compile the template is rendered once for a full and once for a sparse synthetic programme, so a
    template that fails at render time is rejected before it is stored (D-10). Empty optional fields alone never fail.
    """
    template = compile_template(
        text, max_length=MAX_DESCRIPTION_TEMPLATE_LENGTH if description else MAX_TITLE_TEMPLATE_LENGTH
    )
    for sample in (SAMPLE_FULL, SAMPLE_SPARSE):
        try:
            template.render(**template_values(sample, _SAMPLE_CHANNEL, tz=UTC))
        except Exception as err:  # user template code can raise anything; BLE001 does not fire as it is re-raised
            detail = f"{type(err).__name__}: {err}"
            raise TemplateError(TEMPLATE_RUNTIME_ERROR, detail[:_MAX_RUNTIME_DETAIL]) from err


def template_values(programme: Programme, channel: Channel | None, *, tz: tzinfo | None = None) -> dict[str, Any]:
    """
    Return the template variables of a programme: flat, typed, every name of VARIABLE_ORDER always present (D-05).

    Missing text is an empty string and missing lists are empty. start and end stay as parsed, in the zone of the feed
    offset, unless the caller passes its local zone.
    """
    start, end = programme.start, programme.stop
    if tz is not None:
        start, end = start.astimezone(tz), end.astimezone(tz)
    return {
        "channel": channel.display_name if channel is not None else programme.channel_id,
        "channel_id": programme.channel_id,
        "title": programme.title,
        "titles": list(programme.titles),
        "subtitle": programme.sub_titles[0] if programme.sub_titles else "",
        "subtitles": list(programme.sub_titles),
        "episode": programme.episode or "",
        "category": ", ".join(programme.categories),
        "categories": list(programme.categories),
        "description": programme.description or "",
        "start": start,
        "end": end,
    }


@dataclass(slots=True)
class _RenderLog:
    """Holds the calendar name and whether its one render WARNING was already logged (A11)."""

    name: str | None
    warned: bool = False

    def failed(self, kind: str, err: Exception) -> None:
        """Log a render failure: one WARNING per calendar, naming the exception type only, later ones at DEBUG."""
        if self.name is None or self.warned:
            _LOGGER.debug("Calendar %s: %s template failed to render (%s)", self.name, kind, type(err).__name__)
            return
        self.warned = True
        _LOGGER.warning(
            "Calendar %s: %s template failed to render (%s), using the fallback", self.name, kind, type(err).__name__
        )


def _stored(text: str, kind: str, max_length: int, name: str | None) -> Template | None:
    """Compile a stored template; unusable text (legacy syntax, hand-edited storage) is None after one WARNING."""
    try:
        return compile_template(text, max_length=max_length)
    except TemplateError as err:
        if name is not None:  # the flow preview builds templates without a name and stays quiet
            _LOGGER.warning(
                "Calendar %s: stored %s template is not usable (%s), using the default", name, kind, err.reason
            )
        return None


_DEFAULT_TITLE = compile_template(DEFAULT_TITLE_TEMPLATE)


@dataclass(frozen=True, slots=True)
class EventTemplates:
    """
    The compiled templates of one calendar: shared by the calendar entity, the matcher and the flow preview (D-01).

    Equality compares the effective template sources only, so a filter-only edit never looks like a template change.
    """

    title_source: str
    description_source: str | None  # None: the default description (EVT-04)
    title: Template = field(compare=False, repr=False)
    description: Template | None = field(default=None, compare=False, repr=False)
    log: _RenderLog = field(default_factory=lambda: _RenderLog(None), compare=False, repr=False)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object], name: str | None = None) -> EventTemplates:
        """
        Build from stored subentry data; an unusable stored template logs one WARNING naming `name`, then falls back.

        Without a name nothing is logged (the flow preview). Legacy single-brace text is unusable (D-08), except the
        exact legacy default, which `with_defaults` already maps to the new default.
        """
        settings = with_defaults(data)
        title_source = settings[KEY_TITLE_TEMPLATE]
        title = _stored(title_source, "title", MAX_TITLE_TEMPLATE_LENGTH, name)
        if title is None:
            title_source, title = DEFAULT_TITLE_TEMPLATE, _DEFAULT_TITLE
        description_source = settings[KEY_DESCRIPTION_TEMPLATE] or None
        description = None
        if description_source is not None:
            description = _stored(description_source, "description", MAX_DESCRIPTION_TEMPLATE_LENGTH, name)
            if description is None:
                description_source = None
        return cls(title_source, description_source, title, description, _RenderLog(name))

    def _render(self, template: Template, values: Mapping[str, object], kind: str) -> str | None:
        """Return the rendered text, or None after logging when the template raised (D-03)."""
        try:
            return template.render(**values)
        except Exception as err:  # noqa: BLE001 - user template code can raise anything; one programme must not fail the window
            self.log.failed(kind, err)
            return None

    def render_title(self, programme: Programme, values: Mapping[str, object]) -> str:
        """Return the cleaned title, or the programme title when it fails or renders empty (CalendarEvent needs one)."""
        text = self._render(self.title, values, "title")
        return (clean_title(text) if text is not None else "") or programme.title

    def render_description(self, programme: Programme, values: Mapping[str, object]) -> str | None:
        """Return the templated description, else the default description (EVT-04) also when the template fails."""
        if self.description is None:
            return default_description(programme)
        text = self._render(self.description, values, "description")
        return clean_description(text) if text is not None else default_description(programme)


DEFAULT_TEMPLATES = EventTemplates.from_mapping({})


def event_uid(programme: Programme) -> str:
    """Return `<channel_id>-<UTC start %Y%m%dT%H%M%SZ>-<crc32(title) as 8 hex>`, stable across refreshes (EVT-06)."""
    # Hashes the raw programme title, never the rendered one, so template edits keep UIDs
    start = programme.start.astimezone(UTC)
    return f"{programme.channel_id}-{start:%Y%m%dT%H%M%SZ}-{zlib.crc32(programme.title.encode()):08x}"


def to_event_fields(
    programme: Programme,
    channel: Channel | None,
    templates: EventTemplates = DEFAULT_TEMPLATES,
    *,
    tz: tzinfo | None = None,
) -> EventFields:
    """Return templated summary and description, location = display name else channel ID, and the UID."""
    values = template_values(programme, channel, tz=tz)
    return EventFields(
        summary=templates.render_title(programme, values),
        location=values["channel"],
        description=templates.render_description(programme, values),
        uid=event_uid(programme),
    )
