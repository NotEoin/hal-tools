# hal-calendar

hal-calendar keeps Hal's calendar: events in plain English, reminders pushed to your phone and
spoken aloud, agendas, free-time search and two-way sync with any CalDAV server, Apple iCloud
Calendar included.

## Highlights

- "Dentist thursday at 10", "standup every weekday at 9:30 for 15 minutes", "Sam's birthday 3 March":
  dates, times, lengths and repeats read from plain English, UK style.
- Reminders at any lead time through hal-notify (phone push, desktop, HAL's voice), with a desktop
  and ntfy fallback when hal-notify is not installed.
- Clash warnings, free-slot search within working hours, and agendas for any range.
- Repeating events (daily, weekly on chosen days, monthly, yearly, with a count or end date).
- ICS import and export, written in your time zone with its VTIMEZONE.
- CalDAV sync: pulls events from the calendars you choose, pushes new and edited events, sends deletions.

## Install

hal-calendar needs Python 3.11 or later and nothing from PyPI. Clone it into your ecosystem folder
and start the reminder daemon:

```bash
git clone <url> ~/src/hal-ecosystem/hal-calendar
ln -s ~/src/hal-ecosystem/hal-calendar/systemd/hal-calendar-reminders.service ~/.config/systemd/user/
systemctl --user enable --now hal-calendar-reminders.service
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub calendar_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-calendar
python3 -m halcal add title="Dentist" when_text="thursday at 10" location="Shoreditch"
python3 -m halcal add title="Gym every monday and wednesday at 7am for an hour"
python3 -m halcal agenda span="next 7 days"
python3 -m halcal free duration_minutes=120 span=week
python3 -m halcal move event=Dentist when_text="friday 11am"
```

## Connect Apple iCloud Calendar

iCloud's CalDAV needs an app-specific password rather than your Apple ID password:

1. Sign in at appleid.apple.com, open **Sign-In and Security**, then **App-Specific Passwords**, and create one called "Hal".
2. Connect with your Apple ID email and that password:

   ```bash
   python3 -m halcal setup_caldav username=you@icloud.com password=abcd-efgh-ijkl-mnop push_to=Home
   ```

3. Sync once to check, then let the reminder daemon sync every 15 minutes:

   ```bash
   python3 -m halcal sync
   ```

The password is stored in `~/.config/hal/caldav-password` with owner-only permissions; the URL,
username and target calendar go in `[calendar.caldav]`. Any other CalDAV server (Nextcloud, Fastmail,
Radicale) works the same way with its own URL.

## Configuration

Settings live in the `[calendar]` table of `~/.config/hal/config.toml`:

```toml
[calendar]
timezone = "Europe/London"
default_reminders = [15]        # minutes before a timed event
all_day_reminder_hour = 8       # when an all-day event is announced
sync_minutes = 15

[calendar.caldav]
url = "https://caldav.icloud.com"
username = "you@icloud.com"
password_file = "~/.config/hal/caldav-password"
calendars = ["Home", "Work"]    # which to pull; all by default
push_to = "Home"                # where events made in Hal go
```

## Licence

MIT. See [LICENSE](LICENSE).
