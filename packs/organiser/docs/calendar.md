# hal-calendar

hal-calendar keeps Hal's calendar: events in plain English, reminders pushed to your phone and
spoken aloud, agendas, free-time search and two-way sync with any CalDAV server, Apple iCloud
Calendar included.

## Highlights

- "Dentist thursday at 10", "standup every weekday at 9:30 for 15 minutes", "Sam's birthday 3 March",
  "tomorrow from 2 till 3:30pm": dates, times, ranges, lengths and repeats read from plain English, UK
  style. A bare hour from 1 to 7 is the afternoon unless the morning is named.
- Events are found from loose words: "delete the pottery class on Friday" finds "Pottery class" on
  that day, and when several events fit, Hal is told which so it can ask.
- Reminders at any lead time through hal-notify (phone push, desktop, HAL's voice), with a desktop
  and ntfy fallback when hal-notify is not installed.
- Clash warnings, free-slot search within working hours, and agendas for any range.
- Repeating events (daily, weekly on chosen days, monthly, yearly, with a count or end date).
- ICS import and export, written in your time zone with its VTIMEZONE.
- CalDAV sync: pulls events from the calendars you choose, pushes new and edited events, sends deletions.

## Install

hal-calendar needs Python 3.11 or later and nothing from PyPI. It lives in `extensions/hal-calendar`
and is installed by the ecosystem installer, which renders the units in `systemd/` into
`~/.config/systemd/user` (replacing `@ROOT@` with this folder) and starts them with `hal.target`:

```bash
hal ext add calendar
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub calendar_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-calendar
python3 -m halcal add title="Dentist" when_text="thursday at 10" location="Shoreditch"
python3 -m halcal add title="Gym every monday and wednesday at 7am for an hour"
python3 -m halcal agenda span="next 7 days"
python3 -m halcal free duration_minutes=120 span=week
python3 -m halcal move event=Dentist when_text="friday 11am"
```

## Connect Apple iCloud Calendar

iCloud's CalDAV needs an app-specific password rather than your Apple ID password:

1. Sign in at appleid.apple.com, open **Sign-In and Security**, then **App-Specific Passwords**, and create one called "Hal".
2. Connect from a terminal in this folder (hal-hub is not needed):

   ```bash
   cd ~/src/hal-ecosystem/extensions/hal-calendar
   python3 -m halcal connect
   ```

   It asks for your Apple ID email and then the password, which is not shown as you type and never
   appears in your shell history. It checks them with iCloud before saving anything, lists your
   calendars, asks which one new events from Hal should go to, and runs a first sync. Run it again
   at any time to change the password or that calendar; the settings are updated in place.

3. The reminder daemon then syncs every 15 minutes; `python3 -m halcal sync` syncs straight away.

`--username`, `--push-to NAME` and `--url URL` skip or preset those questions. The password is
stored in `~/.config/hal/caldav-password` with owner-only permissions; the URL, username and target
calendar go in `[calendar.caldav]`. There is deliberately no tool for this, so a password is never
typed into a conversation with Hal. Any other CalDAV server (Nextcloud, Fastmail, Radicale) works
the same way: `python3 -m halcal connect --url https://your.server/dav`.

## Configuration

Settings live in the `[calendar]` table of `~/.config/hal/config.toml`:

```toml
[calendar]
timezone = "Europe/London"
default_reminders = [15]        # minutes before a timed event
all_day_reminder_hour = 8       # when an all-day event is announced
sync_minutes = 15
import_roots = ["~/Documents", "~/Downloads"]   # folders calendar_import and calendar_export may use

[calendar.caldav]
url = "https://caldav.icloud.com"
username = "you@icloud.com"
password_file = "~/.config/hal/caldav-password"
calendars = ["Home", "Work"]    # which to pull; all by default
push_to = "Home"                # where events made in Hal go
```

## Licence

MIT. See [LICENSE](LICENSE).
