# XMLTV Calendar

A Home Assistant custom integration that turns an XMLTV programme guide (EPG) into calendar entities. Each calendar
applies its own filters (channels, include and exclude patterns) and shows the matching broadcasts as events, with the
channel as the event location. Example: "which channel shows Formula 1 next, and when?", visible on the calendar
dashboard and usable in automations.

- One feed download and parse per source, shared by all calendars of that source.
- Plain XML and gzip-compressed feeds (`.xml.gz`) are supported; compression is detected from the file content.
- Every calendar gets a **Next programme** sensor and a **Last fetch** diagnostic sensor, and new matches fire the
  `xmltv_calendar_new_match` event.
- A ready-made blueprint notifies you before a matching programme starts.
- Setup and editing happen in the UI only, in English or German. There is no YAML configuration.

## Requirements

- Home Assistant 2026.3 or newer.
- No Python requirements: the integration uses only Home Assistant and the Python standard library.
- An XMLTV feed, reachable over HTTP(S) or as a local file.

## Installation

Install it as a custom repository in [HACS](https://hacs.xyz):

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/akentner/homeassistant-xmltv-calendar-integration` with the category **Integration**.
3. Download **XMLTV Calendar** and restart Home Assistant.

HACS offers the versions published as
[GitHub releases](https://github.com/akentner/homeassistant-xmltv-calendar-integration/releases); updates show up in
HACS like those of any other integration.

## Adding a source

Go to **Settings > Devices & services > Add integration** and choose **XMLTV Calendar**. A source is one feed; the
calendars are added to it afterwards. Choose the source type:

- **Feed URL**: an `http://` or `https://` address. The feed is downloaded once during setup (with a progress
  dialog), so a wrong URL or a file that is not XMLTV is reported right away.
- **Local file**: an absolute path such as `/media/epg/guide.xml` or `/media/epg/guide.xml.gz`. Home Assistant only
  lets integrations read the media folders and the directories listed in
  [`allowlist_external_dirs`](https://www.home-assistant.io/integrations/homeassistant/#allowlist_external_dirs).

Gzip compression is detected from the content, not from the file name or the server's content type.

### Refresh

**Refresh** offers two modes:

- **Interval**: every 1 to 168 hours.
- **Daily at a fixed time**: once a day at a time such as `18:15`, in the Home Assistant time zone.

The daily time is usually the better choice. An interval is anchored to the last refresh, restart or reload, not to a
time of day, so the refresh time drifts every time Home Assistant restarts. With a daily time you know when new
programmes appear, and you can place the refresh well ahead of the evening programme (see
[Limitations](#limitations)).

To refresh a source at once, call `homeassistant.update_entity` with any entity of the source, for example its
calendar:

```yaml
action: homeassistant.update_entity
target:
  entity_id: calendar.formel_1
```

### Timezone

The collapsed **Timezone** section is only needed when the times in the feed are off:

- **Times without offset**: how to read feed times that carry no UTC offset. **UTC** is the XMLTV default; choose
  **Home Assistant time zone** for feeds that write local times without an offset.
- **Offset correction**: minutes (-720 to 720) added to every programme time, for a feed that is off by a fixed
  amount.

Both settings, and the refresh mode, can be changed later with **Configure** on the source. The URL or path of a source
cannot be changed; add a new source instead.

### Cache and limits

- The last download is kept on disk. After a restart the calendars start from it without waiting for the network;
  a cache that is older than the refresh schedule allows is refreshed shortly after the start.
- Downloads send the server's `ETag` and `Last-Modified` values back (conditional requests). When the feed has not
  changed (HTTP 304 or an identical body), nothing is parsed again.
- Feeds are capped at 256 MiB download and 1 GiB uncompressed.
- A failed refresh is retried after 5 minutes, 15 minutes, 1 hour, 3 hours and then every 6 hours, never later than
  the next regular refresh. The calendars keep showing the last good data. When a source has been failing for more
  than 24 hours, a Repairs issue names the reason and the last successful refresh.

## Adding calendars

On the integration page, choose **Add calendar** on a loaded source (**Edit calendar** changes it later). A calendar
has:

- a **name**, which becomes the entity ID (for example `calendar.formel_1`),
- **Channels**: channel IDs picked from the channels found in the feed,
- **Channel regex**: regular expressions matched against the channel ID, one per line, for example `^sky` or
  `\.de$`. A channel is included when it is picked or matches a channel regex. Leave both empty to include all
  channels.
- **Include**: regular expressions, one per line. A programme is shown when any of them matches. Leave it empty to
  show every programme of the selected channels.
- **Exclude**: regular expressions, one per line. A programme is hidden when any of them matches.

Before saving, a preview shows how many programmes match from now on and the next few of them. Saving is allowed with
zero matches; the calendar fills as soon as matching programmes appear.

### Filter examples

| Goal | Field | Pattern |
|------|-------|---------|
| Formula 1 in German or English titles | Include | `formel\s*1\|formula\s*1` |
| Exactly the title "Tatort", not "Tatort: Die Schöne" | Include | `^Tatort$` |
| Hide repeats | Exclude | `Wiederholung` |
| Only channels whose ID starts with "sky" | Channel regex | `^sky` |

The `\|` in the table is a plain `|` in the form: `formel\s*1|formula\s*1`.

Patterns use Python's regular expression syntax. Each line may be up to 300 characters, with at most 50 lines per
field; an invalid pattern is shown with its error and is never saved. Include and exclude ignore case unless
**Case-sensitive** is set in the advanced options; the channel regex always ignores case. Umlauts match in any Unicode
form either way (a composed `ü` matches a decomposed one), but `ß` does not match `ss`.

### Advanced options

Check **Advanced options** in the calendar form to open a second form:

- **Include searches** and **Exclude searches**: the fields the patterns are matched against: title, sub-title,
  description and category. The default is title and sub-title. Each sub-title and each category is tested on its
  own. Searching descriptions is slower on big feeds.
- **Case-sensitive**: match upper and lower case exactly.
- **From** and **To**: only programmes whose start time lies in this window, in the Home Assistant time zone. A
  window crossing midnight, for example `22:00` to `02:00`, counts for the day it starts. Set both or neither.
- **Weekdays**: only programmes starting on these days. Empty means every day.
- **Minimum duration** and **Maximum duration**: in minutes, inclusive. Empty means no limit.
- **Title template**: the event title. Placeholders: `{channel}`, `{title}`, `{subtitle}`, `{episode}`,
  `{category}`, `{channel_id}`. Default: `{channel}: {title}`.
- **Description template**: the event description, with the same placeholders plus `{description}`. Empty means the
  default description (sub-title, episode, categories and description).
- **Keep past matches (days)**: 0 to 7, default 1. An ended match stays in the calendar for this many days after the
  feed no longer lists it, also across restarts. Limits:
  - A programme the feed still lists is always shown, whatever this value is. Feeds usually keep a programme for a
    while after it ended.
  - Ended matches are captured while Home Assistant runs. If Home Assistant is down for more than a day, matches that
    ended meanwhile can be missing.
  - Changing the source's timezone settings drops the kept matches, because their times were read with the old
    settings.

## Entities

Every calendar is a device with three entities. With a calendar named "Formel 1" in an English Home Assistant
(Home Assistant names new entities in the language it runs in; in German the sensors become
`sensor.formel_1_nachste_sendung` and `sensor.formel_1_letzter_abruf`):

### Calendar (`calendar.formel_1`)

One event per matching programme, with the channel as the location. The state is `on` while a match airs and `off`
otherwise. The entity's attributes (`message`, `start_time`, `end_time`, `location`, `description`) describe only one
event: the current one, or the next one when nothing airs. Use the calendar trigger, `calendar.get_events` or the
sensor below to see more.

### Next programme (`sensor.formel_1_next_programme`)

A timestamp sensor: the start of the next match that has not started yet. It moves on to the following match the
moment a match starts. When the calendar has no upcoming match, the state is `unknown` and the sensor has no match
attributes.

| Attribute | Content |
|-----------|---------|
| `title` | Programme title from the feed |
| `summary` | Event title, rendered with the calendar's title template |
| `channel` | Channel display name |
| `channel_id` | Channel ID from the feed |
| `start`, `end` | Start and end as ISO 8601 strings in Home Assistant's local time |
| `subtitle`, `episode`, `description` | From the feed, or `null` when the feed has none |

`subtitle`, `episode` and `description` are not written to the recorder history.

### Last fetch (`sensor.formel_1_last_fetch`)

A diagnostic timestamp sensor: when the source last ran a refresh. It is **disabled by default**. To enable it, open
the calendar's device, choose the sensor under **Diagnostic**, open its settings and switch on **Enabled**. All
calendars of a source show the same run; only `matches` is the calendar's own.

| Attributes | Content |
|------------|---------|
| `trigger` | What started the run: startup, scheduled, retry, revalidate or manual |
| `outcome`, `http_status`, `failure_reason` | How it ended: downloaded, not modified (304), unchanged, file read, started from cache or failed |
| `cache`, `sent_etag`, `sent_last_modified` | What the disk cache did, and whether the conditional request headers were sent |
| `bytes`, `programmes`, `channels`, `parse_duration` | Size and content of the feed, and the parse time in seconds |
| `last_success`, `next_refresh`, `consecutive_failures` | The source's schedule and failure streak |
| `matches` | Number of feed programmes this calendar matches |

The sensor never shows the URL, host or path of the source.

## Event `xmltv_calendar_new_match`

The event fires once for every match that a refresh adds to a calendar and that has not started yet. It does **not**
fire for the matches a calendar already shows when it is added, when Home Assistant starts, when the source is
reloaded or its options are changed (timezone settings included), or when the calendar's filters are edited. Each
match is announced only once, also across restarts. At most 50 events fire per calendar and refresh, earliest start
first; the rest are logged as a warning and not announced.

| Key | Content |
|-----|---------|
| `entity_id` | The calendar entity, for example `calendar.formel_1` |
| `calendar` | The calendar's name |
| `title` | Programme title from the feed |
| `summary` | Event title, rendered with the calendar's title template |
| `channel` | Channel display name |
| `channel_id` | Channel ID from the feed |
| `start`, `end` | ISO 8601 strings in Home Assistant's local time, for example `2026-10-25T14:00:00+01:00` |
| `uid` | The event's unique ID in the calendar |

`start` and `end` (in the event and in the sensor attributes) are strings, not datetimes. Use `as_datetime` to compute
with them, for example `{{ as_datetime(trigger.event.data.start) - now() }}`.

## Automation examples

### Calendar trigger with an offset

Notify 10 minutes before every match. Programmes that start at the same time each trigger separately, so use
`mode: queued` (or `parallel`), never `single`:

```yaml
alias: Formula 1 starts soon
mode: queued
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.formel_1
    offset: "-00:10:00"
actions:
  - action: notify.send_message
    target:
      entity_id: notify.my_phone
    data:
      title: "{{ trigger.calendar_event.summary }}"
      message: >-
        Starts at {{ as_timestamp(trigger.calendar_event.start) | timestamp_custom('%H:%M') }}
        on {{ trigger.calendar_event.location }}
```

### Next programme sensor

Every evening at 18:00, announce the next match if it starts within the next 6 hours:

```yaml
alias: Tonight's Formula 1
mode: single
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: template
    value_template: >-
      {% set next = states('sensor.formel_1_next_programme') %}
      {{ next not in ['unknown', 'unavailable'] and as_datetime(next) - now() < timedelta(hours=6) }}
actions:
  - action: notify.send_message
    target:
      entity_id: notify.my_phone
    data:
      title: "Tonight: {{ state_attr('sensor.formel_1_next_programme', 'title') }}"
      message: >-
        {{ state_attr('sensor.formel_1_next_programme', 'channel') }} at
        {{ as_timestamp(states('sensor.formel_1_next_programme')) | timestamp_custom('%H:%M') }}
```

### New-match event

Get told when a refresh finds a new match of one calendar:

```yaml
alias: New Tatort found
mode: queued
triggers:
  - trigger: event
    event_type: xmltv_calendar_new_match
    event_data:
      entity_id: calendar.tatort
actions:
  - action: notify.send_message
    target:
      entity_id: notify.my_phone
    data:
      title: "New: {{ trigger.event.data.summary }}"
      message: >-
        {{ trigger.event.data.channel }},
        {{ as_datetime(trigger.event.data.start).strftime('%a %d.%m. %H:%M') }}
```

## Blueprint

The repository ships an automation blueprint, **XMLTV Calendar: notify before a matching programme starts**:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fakentner%2Fhomeassistant-xmltv-calendar-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxmltv_calendar%2Fnotify_before_programme.yaml)

Or import it manually from
`https://github.com/akentner/homeassistant-xmltv-calendar-integration/blob/main/blueprints/automation/xmltv_calendar/notify_before_programme.yaml`.

Inputs:

- **Calendar**: an XMLTV calendar.
- **Lead time**: when to run relative to the programme start. Enter a **negative** duration to run before the start;
  the default is minus 10 minutes.
- **Notify entities**: the notify entities the default action sends to. Without one, the default action does nothing.
- **Actions**: what to run, once per programme. The default sends "Starts at 20:15 on Das Erste" with the event title
  as the notification title. Custom actions can use the variables `title`, `channel`, `start`, `end`, `start_time`
  and `description`.

The blueprint runs in `mode: queued`, so overlapping programmes each run the actions.

If your mobile app offers no notify entity (older Home Assistant or app versions only provide the
`notify.mobile_app_<device>` action), replace the default action with:

```yaml
- action: notify.mobile_app_my_phone
  data:
    title: "{{ title }}"
    message: "Starts at {{ start_time }} on {{ channel }}"
```

## Limitations

- **Calendar triggers read the calendar every 15 minutes.** Home Assistant fetches the events of the next 15 minutes
  in advance. A match that appears in the calendar less than 15 minutes before its trigger time (its start plus the
  offset) may not trigger. Pick a daily refresh time well ahead of the programmes you care about, for example 18:15
  for the evening programme, and use the `xmltv_calendar_new_match` event for matches that are added late.
- **Overlapping programmes each trigger separately.** Two matches that start at the same time, or overlap, fire one
  calendar trigger each. Use `mode: queued` or `parallel`; with `single` the second run is dropped.
- **The calendar's state shows one event.** When programmes overlap, the calendar entity's state and attributes show
  only the one that started first, while the triggers still fire for each. Use the calendar trigger,
  `calendar.get_events` or the Next programme sensor to see the others.
- **An interval refresh drifts.** It is anchored to the last refresh, restart or reload; use the daily refresh time
  when the timing matters, or refresh at once with `homeassistant.update_entity`.
- **No upcoming match:** the Next programme sensor is `unknown` until the feed holds a new match.
- Feed content (titles, descriptions, channel names) is shown as the feed provides it, in the feed's language.

## Diagnostics

On the integration page, open the menu of a source and choose **Download diagnostics**. The file contains the source
type, its options, the refresh health (last success, failure streak, last failure reason), the last refresh run, the
cache metadata (time, size, whether validators are stored), feed statistics and, per calendar, its name with the
number of matches and kept past matches. It never contains feed content or filter patterns. The URL keeps only its
scheme and host, a file path only its file name, and credentials and cache validators are redacted, so the file can be
attached to a bug report.

## Releases

A release is made by pushing a tag of the form `vX.Y.Z`. The tag has to equal the `version` in
`custom_components/xmltv_calendar/manifest.json`; the release workflow fails first when it does not. It then runs the
same checks as every push (Ruff lint and format, the tests) and the validation (hassfest and the HACS validation), and
only when all of them pass does it create the GitHub release with generated notes. A version with a hyphen suffix, for
example `v0.2.0-rc1`, becomes a prerelease, which HACS only offers when beta versions are enabled for this repository.

## License

MIT, see [LICENSE](LICENSE).
