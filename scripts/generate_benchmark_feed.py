# ruff: noqa: INP001  # a standalone script, not a package module
"""
Write a deterministic synthetic XMLTV feed for benchmarks and manual checks (stdlib only).

The output is never committed. Tests write it into a pytest temp directory; for a manual check run, for example:

    uv run python scripts/generate_benchmark_feed.py --output /tmp/feed.xml.gz --gzip --start-date 2026-10-14
"""

import argparse
import gzip
import io
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import IO, TextIO
from xml.sax.saxutils import escape, quoteattr

CHANNEL_PREFIXES = (
    "Sport",
    "Kultur",
    "Nachrichten",
    "Kinder",
    "Doku",
    "Musik",
    "Film",
    "Serien",
    "Wissen",
    "Reise",
    "Küche",
    "Natur",
)
CHANNEL_SUFFIXES = ("Fernsehen", "Kanal", "Plus", "Zwei", "Österreich", "Schweiz", "Süd", "Nord", "Großstadt", "Grün")
WORDS = (
    "Formel",
    "Rennen",
    "Großer",
    "Preis",
    "Qualifying",
    "Training",
    "Fußball",
    "Bundesliga",
    "Länderspiel",
    "Tagesschau",
    "Wetter",
    "Krimi",
    "Tatort",
    "Dokumentation",
    "Natur",
    "Tiere",
    "Reise",
    "Küche",
    "Kochen",
    "Garten",
    "Geschichte",
    "Wissenschaft",
    "Musik",
    "Konzert",
    "Oper",
    "Film",
    "Komödie",
    "Drama",
    "Abenteuer",
    "Familie",
    "Nachrichten",
    "Magazin",
    "Talk",
    "Quiz",
    "Show",
    "Live",
    "Spezial",
    "Folge",
    "Staffel",
    "Wiederholung",
    "über",
    "die",
    "der",
    "das",
    "und",
    "mit",
    "für",
    "im",
    "am",
    "vom",
    "Berg",
    "Meer",
    "Stadt",
    "Land",
    "Fluss",
    "Brücke",
    "Straße",
    "Zukunft",
    "Vergangenheit",
    "Menschen",
)
CATEGORIES = ("Sport", "Nachrichten", "Spielfilm", "Serie", "Dokumentation", "Kinder", "Musik", "Unterhaltung")
CHANNEL_COUNT = 120
OFFSET = "+0200"
DESCRIPTION_CHARS = 500
FLUSH_EVERY = 500  # programmes per write call


def _channels() -> list[tuple[str, str]]:
    """Return 120 (id, display name) pairs, display names with umlauts."""
    names = [f"{prefix} {suffix}" for prefix in CHANNEL_PREFIXES for suffix in CHANNEL_SUFFIXES]
    return [(f"kanal{index:03d}.de", name) for index, name in enumerate(names[:CHANNEL_COUNT], start=1)]


def _description(rng: random.Random) -> str:
    words: list[str] = []
    length = 0
    while length < DESCRIPTION_CHARS:
        word = rng.choice(WORDS)
        words.append(word)
        length += len(word) + 1
    return " ".join(words) + "."


def _programme(rng: random.Random, channel_id: str, start: datetime, stop: datetime, number: int) -> str:
    title = " ".join(rng.sample(WORDS, rng.randint(2, 4)))
    times = f'start="{start:%Y%m%d%H%M%S} {OFFSET}" stop="{stop:%Y%m%d%H%M%S} {OFFSET}"'
    parts = [
        f"  <programme {times} channel={quoteattr(channel_id)}>\n",
        f'    <title lang="de">{escape(title)}</title>\n',
    ]
    if number % 3 == 0:
        parts.append(f'    <sub-title lang="de">{escape(" ".join(rng.sample(WORDS, 3)))}</sub-title>\n')
    parts.append(f'    <desc lang="de">{escape(_description(rng))}</desc>\n')
    parts.append(f'    <category lang="de">{rng.choice(CATEGORIES)}</category>\n')
    if number % 4 == 0:
        parts.append(f'    <episode-num system="onscreen">S{rng.randint(1, 9)} E{rng.randint(1, 30)}</episode-num>\n')
    parts.append("  </programme>\n")
    return "".join(parts)


def _write(out: TextIO, *, target_bytes: int, seed: int, start_date: date) -> int:
    rng = random.Random(seed)  # noqa: S311  # deterministic test data, not cryptography
    channels = _channels()
    header = ['<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="xmltv-calendar-benchmark">\n']
    header += [
        f"  <channel id={quoteattr(channel_id)}>\n"
        f'    <display-name lang="de">{escape(name)}</display-name>\n'
        "  </channel>\n"
        for channel_id, name in channels
    ]
    chunk = "".join(header)
    written = len(chunk.encode())
    out.write(chunk)

    # Naive local times; every timestamp carries the fixed OFFSET, programmes run back to back per channel
    midnight = datetime(start_date.year, start_date.month, start_date.day)  # noqa: DTZ001
    next_start = [midnight] * len(channels)
    count = 0
    buffer: list[str] = []
    while written < target_bytes:
        index = count % len(channels)
        start = next_start[index]
        stop = start + timedelta(minutes=rng.randint(15, 90))
        next_start[index] = stop
        text = _programme(rng, channels[index][0], start, stop, count)
        buffer.append(text)
        written += len(text.encode())
        count += 1
        if len(buffer) >= FLUSH_EVERY:
            out.write("".join(buffer))
            buffer.clear()
    out.write("".join(buffer))
    out.write("</tv>\n")
    return count


def generate(
    path: Path,
    *,
    target_bytes: int = 60 * 1024 * 1024,
    gzip_output: bool = False,
    seed: int = 1,
    start_date: date = date(2026, 10, 13),
) -> int:
    """
    Write a feed of at least `target_bytes` uncompressed XML to `path` and return its programme count.

    The same arguments always produce byte-identical output, gzip included (no mtime or file name in the header).
    """
    with path.open("wb") as raw:
        if gzip_output:
            with (
                gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
                _text(compressed) as out,
            ):
                return _write(out, target_bytes=target_bytes, seed=seed, start_date=start_date)
        with _text(raw) as out:
            return _write(out, target_bytes=target_bytes, seed=seed, start_date=start_date)


def _text(binary: IO[bytes]) -> TextIO:
    return io.TextIOWrapper(binary, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("--output", type=Path, required=True, help="file to write")
    parser.add_argument("--size-mb", type=int, default=60, help="uncompressed size in MiB (default 60)")
    parser.add_argument("--gzip", action="store_true", help="gzip-compress the output")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2026, 10, 13),
        help="first programme day, YYYY-MM-DD (default 2026-10-13)",
    )
    args = parser.parse_args(argv)
    count = generate(
        args.output,
        target_bytes=args.size_mb * 1024 * 1024,
        gzip_output=args.gzip,
        start_date=args.start_date,
    )
    sys.stdout.write(f"Wrote {count} programmes to {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
