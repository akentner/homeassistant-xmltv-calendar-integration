"""SRC-09 benchmark: a generated 60 MB feed parses fast, in bounded memory, without stalling the event loop."""

import asyncio
import importlib.util
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from custom_components.xmltv_calendar.xmltv.parser import parse

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from custom_components.xmltv_calendar.xmltv.model import EpgData

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_benchmark_feed.py"

FEED_BYTES = 60 * 1024 * 1024
MIN_PROGRAMMES = 75_000
MAX_PARSE_SECONDS = 30.0
MAX_PEAK_BYTES = 150 * 1024 * 1024
MAX_LOOP_GAP_SECONDS = 0.250  # CI-generous; the dev box measures about 10 ms with yield_every=250
HEARTBEAT_SECONDS = 0.005
MIN_HEARTBEATS = 20


def _generator() -> ModuleType:
    """Load scripts/generate_benchmark_feed.py by path: scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location("generate_benchmark_feed", GENERATOR)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_file(path: Path) -> EpgData:
    with path.open("rb") as fileobj:
        return parse(fileobj)


def _report(
    record_property: Callable[[str, object], None], capsys: pytest.CaptureFixture[str], label: str, **values: float
) -> None:
    """Attach the measurements to the JUnit report and print them, so the CI log shows them."""
    for name, value in values.items():
        record_property(name, value)
    with capsys.disabled():
        sys.stdout.write(f"\n[benchmark] {label}: " + ", ".join(f"{k}={v}" for k, v in values.items()) + "\n")


@pytest.fixture(scope="session", params=["plain", "gzip"])
def benchmark_feed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A 60 MB (uncompressed) feed written outside the repository; generated once per variant and session."""
    gzip_output = request.param == "gzip"
    path = tmp_path_factory.mktemp("benchmark") / ("feed.xml.gz" if gzip_output else "feed.xml")
    _generator().generate(path, target_bytes=FEED_BYTES, gzip_output=gzip_output)
    return path


@pytest.mark.parametrize("gzip_output", [False, True], ids=["plain", "gzip"])
def test_generator_is_deterministic(tmp_path: Path, gzip_output: bool) -> None:
    generate = _generator().generate
    first, second = tmp_path / "first", tmp_path / "second"
    count_first = generate(first, target_bytes=200_000, gzip_output=gzip_output, seed=1)
    count_second = generate(second, target_bytes=200_000, gzip_output=gzip_output, seed=1)
    assert count_first == count_second > 0
    assert first.read_bytes() == second.read_bytes()


def test_generated_feed_is_valid_xmltv(tmp_path: Path) -> None:
    path = tmp_path / "small.xml"
    count = _generator().generate(path, target_bytes=200_000, start_date=date(2026, 3, 1))
    assert path.stat().st_size >= 200_000
    data = _parse_file(path)
    assert data.stats.programmes == count
    assert data.stats.skipped_malformed == 0
    assert data.stats.channels == 120
    assert any(ch in channel.display_name for channel in data.channels.values() for ch in "äöüÄÖÜß")
    first_start = min(programme.start for programme in data.programmes)
    assert first_start == datetime(2026, 2, 28, 22, 0, tzinfo=UTC)  # 2026-03-01 00:00 +0200


@pytest.mark.benchmark
def test_parse_large_feed_time_and_memory(
    benchmark_feed: Path, record_property: Callable[[str, object], None], capsys: pytest.CaptureFixture[str]
) -> None:
    tracemalloc.start()
    try:
        started = time.perf_counter()
        data = _parse_file(benchmark_feed)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    _report(
        record_property,
        capsys,
        f"{benchmark_feed.name} time/memory",
        parse_seconds_under_tracemalloc=round(elapsed, 2),
        tracemalloc_peak_mb=round(peak / 1024 / 1024, 1),
        programmes=data.stats.programmes,
        file_mb=round(benchmark_feed.stat().st_size / 1024 / 1024, 1),
    )
    assert data.stats.programmes >= MIN_PROGRAMMES
    assert elapsed < MAX_PARSE_SECONDS
    assert peak < MAX_PEAK_BYTES


@pytest.mark.benchmark
async def test_event_loop_stays_responsive(
    benchmark_feed: Path, record_property: Callable[[str, object], None], capsys: pytest.CaptureFixture[str]
) -> None:
    loop = asyncio.get_running_loop()
    gaps: list[float] = []
    done = asyncio.Event()

    async def heartbeat() -> None:
        last = time.perf_counter()
        while not done.is_set():
            await asyncio.sleep(HEARTBEAT_SECONDS)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now

    with ThreadPoolExecutor(max_workers=1) as executor:
        beat = asyncio.create_task(heartbeat())
        await asyncio.sleep(0)
        started = time.perf_counter()
        data = await loop.run_in_executor(executor, _parse_file, benchmark_feed)
        elapsed = time.perf_counter() - started
        done.set()
        await beat

    max_gap = max(gaps)
    _report(
        record_property,
        capsys,
        f"{benchmark_feed.name} event loop",
        parse_seconds=round(elapsed, 2),
        max_loop_gap_ms=round(max_gap * 1000, 1),
        heartbeats=len(gaps),
    )
    assert data.stats.programmes >= MIN_PROGRAMMES
    assert len(gaps) >= MIN_HEARTBEATS
    assert max_gap < MAX_LOOP_GAP_SECONDS
