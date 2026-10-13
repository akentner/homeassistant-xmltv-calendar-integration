# XMLTV Calendar

A Home Assistant custom integration that turns an XMLTV programme guide (EPG) into calendar entities. Each calendar
applies its own filters (channels, include and exclude patterns on title and description) and shows the matching
broadcasts as events, with the channel as the event location. Example: "which channel shows Formula 1 next, and
when?", visible on the calendar dashboard and usable as a calendar trigger in automations.

- One feed download and parse per source, shared by all calendars of that source.
- Plain XML and gzip-compressed feeds (`.xml.gz`) are supported; compression is detected from the file content.
- Setup and editing happen in the UI only. There is no YAML configuration.

Requires Home Assistant 2026.3 or newer.

## Installation

Install it as a custom repository in [HACS](https://hacs.xyz):

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/akentner/homeassistant-xmltv-integration` with the category **Integration**.
3. Download **XMLTV Calendar** and restart Home Assistant.

## Adding a source

Go to **Settings > Devices & services > Add integration** and choose **XMLTV Calendar**. A source is either:

- a **URL** (`http://` or `https://`) of an XMLTV file, or
- a **local file** under a path Home Assistant may read, such as `/media`. Other directories must be listed in
  [`allowlist_external_dirs`](https://www.home-assistant.io/integrations/homeassistant/#allowlist_external_dirs).

Each source has its own refresh interval. Feeds are capped at 256 MiB download and 1 GiB uncompressed.

## Adding calendars

On the integration page, choose **Add calendar** on a loaded source. A calendar has:

- a **name**, which becomes the entity ID (for example `calendar.formel_1`),
- the **channels** to include, picked from the channels found in the feed (empty means all channels),
- optional **include** and **exclude** patterns (regular expressions) matched against title and description.

Every matching programme becomes one calendar event. Use the exclude pattern to drop unwanted entries such as
repeats or previews.

A full guide to filter patterns and calendar-trigger automations follows in a later release.

## License

MIT, see [LICENSE](LICENSE).
