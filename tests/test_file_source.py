"""Local file sources: re-parse only when the file changed, allowed-path check on every refresh (D-11)."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xmltv_calendar import coordinator as coordinator_module
from custom_components.xmltv_calendar import source as source_module

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

FEED = (Path(__file__).parent / "fixtures" / "basic.xml").read_bytes()
NOW = "2026-10-13T06:00:00+00:00"
DOMAIN = "xmltv_calendar"
pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("forbid_loop_io")]


class ParseCounter:
    """Counts feed parses, whichever module the file read looks `parse` up in."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wrap the real parser in the coordinator and source modules."""
        self.calls = 0
        real = coordinator_module.parse

        def counting(*args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(coordinator_module, "parse", counting)
        monkeypatch.setattr(source_module, "parse", counting)


@pytest.fixture
def feed_path(tmp_path: Path) -> Path:
    """Write the feed into a resolved temporary directory (is_allowed_path compares resolved paths)."""
    path = tmp_path.resolve() / "guide.xml"
    path.write_bytes(FEED)
    return path


@pytest.fixture
async def file_entry(hass: HomeAssistant, feed_path: Path) -> MockConfigEntry:
    """Set up a file source entry with one calendar, its directory on the allowlist."""
    hass.config.allowlist_external_dirs = {str(feed_path.parent)}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Local",
        data={"source_type": "file", "path": str(feed_path)},
        options={"refresh_hours": 24},
        subentries_data=[ConfigSubentryData(subentry_type="calendar", title="Test", data={}, unique_id=None)],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def _bump_mtime(path: Path) -> None:
    mtime = path.stat().st_mtime
    os.utime(path, (mtime, mtime + 60))


def _append_keeping_mtime(path: Path) -> None:
    """Grow the file but restore its mtime, so only the size tells the change."""
    stat = path.stat()
    path.write_bytes(FEED + b"<!-- appended -->\n")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def _payload_files(hass: HomeAssistant) -> list[Path]:
    return list(Path(hass.config.cache_path(DOMAIN)).glob("**/*.feed"))


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_unchanged_file_is_not_reparsed(
    hass: HomeAssistant, file_entry: MockConfigEntry, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator = file_entry.runtime_data.coordinator
    previous = coordinator.data
    parses = ParseCounter(monkeypatch)

    await _refresh(hass, file_entry)

    assert parses.calls == 0
    assert coordinator.data is previous
    assert coordinator.last_update_success is True


async def test_changed_mtime_reparses(
    hass: HomeAssistant, file_entry: MockConfigEntry, feed_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator = file_entry.runtime_data.coordinator
    previous = coordinator.data
    parses = ParseCounter(monkeypatch)
    _bump_mtime(feed_path)

    await _refresh(hass, file_entry)

    assert parses.calls == 1
    assert coordinator.data is not previous
    assert coordinator.last_update_success is True


async def test_changed_size_reparses(
    hass: HomeAssistant, file_entry: MockConfigEntry, feed_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator = file_entry.runtime_data.coordinator
    parses = ParseCounter(monkeypatch)
    _append_keeping_mtime(feed_path)

    await _refresh(hass, file_entry)

    assert parses.calls == 1
    assert coordinator.last_update_success is True


async def test_allowed_path_checked_on_every_refresh(hass: HomeAssistant, file_entry: MockConfigEntry) -> None:
    coordinator = file_entry.runtime_data.coordinator
    previous = coordinator.data
    hass.config.allowlist_external_dirs = set()

    await _refresh(hass, file_entry)

    assert coordinator.last_update_success is False
    assert coordinator.last_exception is not None
    assert coordinator.last_exception.translation_key == "path_not_allowed"
    assert coordinator.data is previous


async def test_reload_parses_file_again(
    hass: HomeAssistant, file_entry: MockConfigEntry, monkeypatch: pytest.MonkeyPatch
) -> None:
    parses = ParseCounter(monkeypatch)

    assert await hass.config_entries.async_reload(file_entry.entry_id)
    await hass.async_block_till_done()

    assert file_entry.state is ConfigEntryState.LOADED
    assert parses.calls == 1


async def test_file_source_writes_no_payload_cache(hass: HomeAssistant, file_entry: MockConfigEntry) -> None:
    await _refresh(hass, file_entry)

    assert not _payload_files(hass)
    assert file_entry.runtime_data.coordinator.cache_meta is None
