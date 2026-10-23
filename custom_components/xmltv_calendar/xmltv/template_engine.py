"""
Sandboxed Jinja2 engine for event titles and descriptions (pure: no Home Assistant imports).

Templates are admin-supplied code that runs inside `ImmutableSandboxedEnvironment`. The sandbox only restricts
attribute access, not resources, so `compile_template` also checks the parsed tree against an explicit allow-list of
node classes, filters and tests before anything is compiled or evaluated (D-04, T-05-01, T-05-02). Feed text is only
ever a variable value, never template source (T-05-04).
"""

import re
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import jinja2
from jinja2 import meta, nodes
from jinja2.sandbox import ImmutableSandboxedEnvironment

from .filter import MAX_PATTERN_LENGTH, NESTED_REPETITION_MESSAGE, PATTERN_ERRORS, has_nested_repeat

if TYPE_CHECKING:
    from collections.abc import Callable

# TemplateError reasons, also the flow's form error keys (D-10)
INVALID_TEMPLATE = "invalid_template"
UNKNOWN_PLACEHOLDER = "unknown_placeholder"
UNSUPPORTED_SYNTAX = "unsupported_syntax"
UNKNOWN_FILTER = "unknown_filter"
LEGACY_PLACEHOLDER = "legacy_placeholder"
TEMPLATE_RUNTIME_ERROR = "template_runtime_error"
TEMPLATE_ERROR_REASONS = (
    INVALID_TEMPLATE,
    UNKNOWN_PLACEHOLDER,
    UNSUPPORTED_SYNTAX,
    UNKNOWN_FILTER,
    LEGACY_PLACEHOLDER,
    TEMPLATE_RUNTIME_ERROR,
)

# The flat, typed variables of a programme (D-05), in documentation order
VARIABLE_ORDER = (
    "channel",
    "channel_id",
    "title",
    "titles",
    "subtitle",
    "subtitles",
    "episode",
    "category",
    "categories",
    "description",
    "start",
    "end",
)
VARIABLES = frozenset(VARIABLE_ORDER)

# The format of the time filter when none is given
DEFAULT_TIME_FORMAT = "%H:%M"

# A1: bounds on the compile cost of admin-supplied text
MAX_TITLE_TEMPLATE_LENGTH = 2000
MAX_DESCRIPTION_TEMPLATE_LENGTH = 5000

# Node classes a template may contain; everything else is unsupported_syntax. Deliberately absent: Call (A6, every
# operation is a filter), Mul, Pow, Mod and Add (A7, resource use), Dict and Pair, and every statement but If, Assign
# and Output (D-04): for, macro, call blocks, include, import, extends, block, with, filter blocks, block-set
ALLOWED_NODES = (
    nodes.Template,
    nodes.Output,
    nodes.TemplateData,
    nodes.If,
    nodes.Assign,
    nodes.Name,
    nodes.Const,
    nodes.Tuple,
    nodes.List,
    nodes.Getattr,
    nodes.Getitem,
    nodes.Slice,
    nodes.Filter,
    nodes.Test,
    nodes.Keyword,
    nodes.CondExpr,
    nodes.Concat,
    nodes.Sub,
    nodes.Div,
    nodes.FloorDiv,
    nodes.And,
    nodes.Or,
    nodes.Not,
    nodes.Neg,
    nodes.Pos,
    nodes.Compare,
    nodes.Operand,
)
_ALLOWED_NODES = frozenset(ALLOWED_NODES)

STANDARD_FILTERS = frozenset(
    {
        "abs",
        "capitalize",
        "count",
        "d",
        "default",
        "first",
        "int",
        "join",
        "last",
        "length",
        "list",
        "lower",
        "map",
        "max",
        "min",
        "reject",
        "replace",
        "reverse",
        "round",
        "select",
        "sort",
        "string",
        "title",
        "trim",
        "truncate",
        "unique",
        "upper",
        "wordcount",
    }
)
STANDARD_TESTS = frozenset(
    {
        "defined",
        "undefined",
        "none",
        "string",
        "number",
        "integer",
        "eq",
        "equalto",
        "ne",
        "ge",
        "gt",
        "le",
        "lt",
        "in",
        "sameas",
        "lower",
        "upper",
        "odd",
        "even",
    }
)

# Filters whose first argument is a regex pattern that must be a text literal, and the position of their ignorecase
# argument (assumption A8: regex_search answers with a boolean)
REGEX_FILTERS = ("regex_replace", "regex_search")
_IGNORECASE_POSITION = {"regex_replace": 2, "regex_search": 1}

# Placeholders of the retired single-brace syntax (D-08); only these names could ever be stored
_LEGACY_PLACEHOLDER = re.compile(r"\{(channel_id|channel|title|subtitle|episode|category|description)\}")


class TemplateError(ValueError):
    """A template that cannot be used; `reason` is a flow error key, `detail` the offending part."""

    def __init__(self, reason: str, detail: str) -> None:
        """Store the flow error key and the detail."""
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _text(value: object) -> str:
    """Return `value` as text; None and undefined values are the empty string (D-03, D-06)."""
    if value is None or isinstance(value, jinja2.Undefined):
        return ""
    return value if isinstance(value, str) else str(value)


@lru_cache(maxsize=128)
def _pattern(pattern: str, flags: int) -> re.Pattern[str]:
    return re.compile(pattern, flags)


def regex_replace(value: object, find: object, replace: object = "", ignorecase: object = False) -> str:  # noqa: FBT002
    """Replace every match of the regex `find` in `value`; same signature as Home Assistant's own filter."""
    flags = re.IGNORECASE if ignorecase else 0
    return _pattern(_text(find), flags).sub(_text(replace), _text(value))


def lines(value: object) -> list[str]:
    """Return the text as a list of lines, each stripped, blank ones dropped (A9)."""
    return [line for raw in _text(value).splitlines() if (line := raw.strip())]


def first_line(value: object) -> str:
    """Return the first non-blank line, stripped, or the empty string (A9)."""
    return next(iter(lines(value)), "")


def split(value: object, sep: object = None, maxsplit: object = -1) -> list[str]:
    """
    Return the text split at `sep` (whitespace when omitted) at most `maxsplit` times; missing text is an empty list.

    An empty or non-text separator returns the whole text as one element instead of raising.
    """
    text = _text(value)
    if not text:
        return []
    limit = maxsplit if isinstance(maxsplit, int) else -1
    if sep is None or isinstance(sep, jinja2.Undefined):
        return text.split(None, limit)
    separator = _text(sep)
    return text.split(separator, limit) if separator else [text]


def regex_search(value: object, find: object, ignorecase: object = False) -> bool:  # noqa: FBT002
    """Return whether the regex `find` matches anywhere in `value` (A8: a boolean, for use behind if)."""
    flags = re.IGNORECASE if ignorecase else 0
    return _pattern(_text(find), flags).search(_text(value)) is not None


def strip_prefix(value: object, text: object) -> str:
    """Remove `text` once from the start of `value`; unchanged when it does not match or `text` is empty."""
    return _text(value).removeprefix(_text(text))


def strip_suffix(value: object, text: object) -> str:
    """Remove `text` once from the end of `value`; unchanged when it does not match or `text` is empty."""
    return _text(value).removesuffix(_text(text))


def remove(value: object, *parts: object) -> str:
    """Delete every occurrence of each non-empty part from `value`, in order."""
    result = _text(value)
    for part in parts:
        if text := _text(part):
            result = result.replace(text, "")
    return result


def format_time(value: object, fmt: object = DEFAULT_TIME_FORMAT) -> str:
    """
    Return `value` formatted with strftime in its own zone, or the empty string when it is not a datetime.

    The caller converts start and end to the local zone before rendering, so no zone or clock is read here (D-06). Only
    numeric directives are documented: the names of months and weekdays follow the process locale (A3).
    """
    if not isinstance(value, datetime):  # not hasattr: an undefined value answers hasattr and would raise
        return ""
    return value.strftime(fmt if isinstance(fmt, str) else DEFAULT_TIME_FORMAT)


# Filter functions come first, so later plans only add functions and registry entries
CUSTOM_FILTERS: dict[str, Callable[..., Any]] = {
    "regex_replace": regex_replace,
    "regex_search": regex_search,
    "strip_prefix": strip_prefix,
    "strip_suffix": strip_suffix,
    "remove": remove,
    "split": split,
    "lines": lines,
    "first_line": first_line,
    "time": format_time,
}


def _build_env() -> ImmutableSandboxedEnvironment:
    # No autoescape argument: the output is plain text and the default is already off. ChainableUndefined keeps
    # {{ missing.attr }} and {{ categories[5] }} empty (D-03); trim_blocks and lstrip_blocks keep a block tag on its
    # own line from leaving a blank line (A2)
    env = ImmutableSandboxedEnvironment(undefined=jinja2.ChainableUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters = {name: func for name, func in env.filters.items() if name in STANDARD_FILTERS} | CUSTOM_FILTERS
    env.tests = {name: func for name, func in env.tests.items() if name in STANDARD_TESTS}
    env.globals = {}  # drops range, dict, lipsum, cycler, joiner and namespace
    return env


ENV = _build_env()


def _check_node_class(node: nodes.Node) -> None:
    if type(node) not in _ALLOWED_NODES:
        raise TemplateError(UNSUPPORTED_SYNTAX, f"{type(node).__name__} (line {node.lineno})")


def _check_name(node: nodes.Name) -> None:
    if node.name == "self":
        raise TemplateError(UNSUPPORTED_SYNTAX, f"the name self (line {node.lineno})")


def _check_no_star_arguments(node: nodes.Filter | nodes.Test) -> None:
    if node.dyn_args is not None or node.dyn_kwargs is not None:
        raise TemplateError(UNSUPPORTED_SYNTAX, f"star-arguments (line {node.lineno})")


def _argument(node: nodes.Filter, position: int, keyword: str) -> nodes.Expr | None:
    """Return the argument at `position`, else the keyword argument `keyword`, else None."""
    if len(node.args) > position:
        return node.args[position]
    return next((item.value for item in node.kwargs if item.key == keyword), None)


def _literal_text(node: nodes.Expr | None) -> str | None:
    return node.value if isinstance(node, nodes.Const) and isinstance(node.value, str) else None


def _error_message(err: Exception) -> str:
    return err.msg if isinstance(err, re.error) else str(err)


def _probe_pattern(pattern: str, flags: int, line: int) -> re.Pattern[str]:
    """Return the compiled pattern, or raise for one over the caps, invalid or nesting repetition (T-05-03)."""
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise TemplateError(INVALID_TEMPLATE, f"pattern longer than {MAX_PATTERN_LENGTH} characters (line {line})")
    try:
        compiled = re.compile(pattern, flags)
    except PATTERN_ERRORS as err:
        raise TemplateError(INVALID_TEMPLATE, f"invalid pattern: {_error_message(err)} (line {line})") from None
    if has_nested_repeat(pattern):
        raise TemplateError(INVALID_TEMPLATE, NESTED_REPETITION_MESSAGE)
    return compiled


def _check_regex_arguments(node: nodes.Filter) -> None:
    pattern = _literal_text(_argument(node, 0, "find"))
    if pattern is None:
        raise TemplateError(UNSUPPORTED_SYNTAX, f"the regex pattern must be a text literal (line {node.lineno})")
    ignorecase = _argument(node, _IGNORECASE_POSITION[node.name], "ignorecase")
    flags = re.IGNORECASE if isinstance(ignorecase, nodes.Const) and ignorecase.value else 0
    compiled = _probe_pattern(pattern, flags, node.lineno)
    replacement = _literal_text(_argument(node, 1, "replace")) if node.name == "regex_replace" else None
    if replacement is not None:
        try:
            compiled.sub(replacement, "")  # a bad group reference raises even without a match
        except PATTERN_ERRORS as err:
            raise TemplateError(INVALID_TEMPLATE, f"invalid replacement: {_error_message(err)}") from None


def _check_filter(node: nodes.Filter) -> None:
    if node.name not in ENV.filters:
        raise TemplateError(UNKNOWN_FILTER, node.name)
    _check_no_star_arguments(node)
    if node.name in REGEX_FILTERS:
        _check_regex_arguments(node)


def _check_test(node: nodes.Test) -> None:
    if node.name not in ENV.tests:
        raise TemplateError(UNKNOWN_FILTER, node.name)
    _check_no_star_arguments(node)


def _check_tree(tree: nodes.Template) -> None:
    """Walk every node before anything is compiled, so nothing is constant-folded or evaluated (T-05-02)."""
    for node in tree.find_all(nodes.Node):
        _check_node_class(node)
        if isinstance(node, nodes.Name):
            _check_name(node)
        elif isinstance(node, nodes.Filter):
            _check_filter(node)
        elif isinstance(node, nodes.Test):
            _check_test(node)


def _check_variables(tree: nodes.Template) -> None:
    """Reject variables that are neither known nor assigned in the template (A4: catches a typo such as titel)."""
    unknown = meta.find_undeclared_variables(tree) - VARIABLES
    if unknown:
        raise TemplateError(UNKNOWN_PLACEHOLDER, ", ".join(sorted(unknown)))


def _check_legacy(text: str) -> None:
    """Reject the retired single-brace syntax, which Jinja would render literally (D-08)."""
    if "{{" in text or "{%" in text:
        return
    if (match := _LEGACY_PLACEHOLDER.search(text)) is not None:
        raise TemplateError(LEGACY_PLACEHOLDER, match[0])


def compile_template(text: str, *, max_length: int = MAX_TITLE_TEMPLATE_LENGTH) -> jinja2.Template:
    """
    Return the compiled template, or raise a TemplateError whose reason is a flow error key.

    Stages: length cap, legacy syntax, parse, allow-list walk, undeclared variables, compile from the checked tree.
    """
    if len(text) > max_length:
        raise TemplateError(INVALID_TEMPLATE, f"longer than {max_length} characters")
    _check_legacy(text)
    try:
        tree = ENV.parse(text)
        _check_tree(tree)
        _check_variables(tree)
        return ENV.from_string(tree)
    except jinja2.TemplateSyntaxError as err:
        raise TemplateError(INVALID_TEMPLATE, f"line {err.lineno}: {err.message or 'syntax error'}") from None
    except SyntaxError, RecursionError:  # Python's own compile() limits for pathological nesting
        raise TemplateError(INVALID_TEMPLATE, "the template is too complex") from None
