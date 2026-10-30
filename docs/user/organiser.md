# organiser

The `organiser` pack: calendar, tasks, clock, notifications, briefings and routines. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-organiser   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## briefing

hal-briefing gives you a morning and an evening briefing: the weather, the day's calendar, tasks due,
the job search, headlines and anything wrong with the computer. Hal speaks it, pushes it to your
phone and writes it into the day's note in the vault.

### Highlights

- Gathers each part through hal-hub, so a module that is not installed is simply left out.
- Written to be spoken: short sentences, no lists or symbols.
- Morning: weather, today's events, tasks, job search, headlines, computer health.
- Evening: tomorrow's events, tasks still open, tomorrow's weather, job search.
- Midday: a short job-search update (`kind=jobs`), from hal-jobs.
- Timers for 08:05, 13:00 and 18:00, and on demand: "Hal, brief me." The morning one runs at 08:05
  so it falls after quiet hours (hal-notify's `quiet_until`, 08:00 by default) and is spoken.
- Waits for HAL's voice server when it is still starting after login, so the first briefing is heard.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub briefing_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-briefing
python3 -m halbrief build kind=morning
python3 -m halbrief brief kind=evening speak=false
python3 -m halbrief build kind=jobs
```

### Configuration

Settings live in the `[briefing]` table of `~/.config/hal/config.toml`:

```toml
[briefing]
name = "Dave"      # how the briefing addresses you; empty uses [hal].user_name
```

Change the times by editing the timer units in `systemd/` and reinstalling them.

## calendar

hal-calendar keeps Hal's calendar: events in plain English, reminders pushed to your phone and
spoken aloud, agendas, free-time search and two-way sync with any CalDAV server, Apple iCloud
Calendar included.

### Highlights

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

### Use

The tools run from the module folder, or through hal-hub as `hal-hub calendar_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-calendar
python3 -m halcal add title="Dentist" when_text="thursday at 10" location="Shoreditch"
python3 -m halcal add title="Gym every monday and wednesday at 7am for an hour"
python3 -m halcal agenda span="next 7 days"
python3 -m halcal free duration_minutes=120 span=week
python3 -m halcal move event=Dentist when_text="friday 11am"
```

### Connect Apple iCloud Calendar

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

### Configuration

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

## clock

hal-clock gives Hal timers, alarms, a stopwatch and Pomodoro sessions. When one goes off, Hal says
so aloud and the alert reaches your phone and desktop, even during quiet hours.

### Highlights

- Timers with names and natural lengths: "9 minutes", "1h30", "an hour and a half", "2:30".
- Alarms at a time, one-off or repeating ("7 tomorrow morning", "every weekday at 7"), and snooze. A
  bare hour is the morning: "at 7" wakes you at 07:00.
- A stopwatch with laps, and Pomodoro sessions that announce each break and return to work.
- A one-second daemon, so timers fire on time; state lives in SQLite and survives restarts.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub clock_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-clock
python3 -m halclock timer duration="9 minutes" label=pasta
python3 -m halclock alarm when_text="every weekday at 7am" label="Wake up"
python3 -m halclock pomodoro action=start work=25 rest=5 rounds=4
python3 -m halclock list
```

### Configuration

hal-clock has no settings of its own; alerts follow hal-notify's channels.

## notify

hal-notify routes Hal's alerts to the right places: your phone through ntfy, the desktop and HAL's
voice. It respects quiet hours and do-not-disturb, lets urgent alerts through, and keeps
a history.

### Highlights

- One call reaches every channel you configure; each module that alerts uses it when it is installed.
- Quiet hours (22:00 to 08:00 by default) and do-not-disturb silence phone pushes and speech; urgent alerts still sound.
- Spoken alerts through the command in `[notify].say_command`. There is no Telegram channel; the
  Telegram bridge is a chat, not an alert sink.
- A history of every alert sent and the channels it reached.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub notify_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-notify
python3 -m halnotify send title="Build finished" body="All tests passed" speak=true
python3 -m halnotify dnd minutes=90
python3 -m halnotify state
python3 -m halnotify history limit=5
```

### Configuration

Settings live in the `[notify]` table of `~/.config/hal/config.toml`:

```toml
[notify]
ntfy_topic = "hal-a-long-random-name"
ntfy_server = "https://ntfy.sh"
channels = ["desktop", "phone"]     # add "voice" to use it by default
say_command = ""                    # command that speaks its last argument; empty disables voice
quiet_from = 22
quiet_until = 8
```

Anyone who knows the ntfy topic can read the alerts, so keep it unguessable.

## routines

hal-routines makes Hal proactive. A scene sets several things at once ("focus" silences
notifications, warms the lights, pauses music and starts a Pomodoro); schedules run a scene or any
tool at a time; triggers run one when something happens, such as the computer going idle or a USB
drive appearing.

### Highlights

- Built-in scenes: focus, relax, goodnight, away and movie, and any number you make by asking Hal.
- Every step is its own hub call, so policy decides it. A step that needs approval is skipped,
  not forced, and one notification names it.
- Schedules in plain English: "every weekday at 8:45", "at 23:30".
- Triggers: idle, usb_added, offline, online, disk_full and login.
- Saving a scene, schedule or trigger asks you first. The prompt shows every step, and approving
  it grants those exact steps to run unattended. Editing the steps voids the grant, so the new
  version asks again.
- The built-in scenes use only steps that are allowed by default, so they run unattended.

### Use

Run a tool by hand through the hub, for example `hal-organiser call routines_run name=focus`.
A schedule or trigger takes its steps as JSON:

```bash
hal-organiser call routines_schedule when_text="every day at 23:30" label=goodnight \
  steps='{"tool": "routines_run", "args": {"name": "goodnight"}}'   # run a scene each night
hal-organiser call routines_add_trigger event=usb_added label=usb-note \
  steps='{"tool": "notify_send", "args": {"title": "USB drive connected"}}'   # notify on a new USB device
```

The commands are checked against the manifest and the CLI source, not run (unverified).

### Configuration

Settings live in the `[routines]` table of `~/.config/hal/config.toml`; built-in scenes can be
replaced there:

```toml
[routines]
idle_minutes = 15
[[routines.scenes.reading]]
tool = "rgb_colour"
args = { colour = "warm white", brightness = 60 }
```

## tasks

hal-tasks is Hal's to-do list: tasks in plain English with due dates, priorities, projects and
repeats, reminders when a timed task falls due, and a note in your Obsidian vault where ticking a box
marks the task done.

### Highlights

- "Buy milk tomorrow", "water the plants every monday at 9": due dates and repeats read from the words.
- Completing a repeating task schedules the next one.
- Lists for today (due today or earlier), overdue, upcoming, done this week, by project or tag.
- A morning alert with the day's tasks, and a reminder before each timed task, through hal-notify.
- `Tasks.md` in the vault lists open tasks by project as checkboxes; tick one in Obsidian and Hal
  marks it done.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub tasks_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-tasks
python3 -m haltasks add title="Buy milk tomorrow"
python3 -m haltasks add title="Water the plants" due="every monday at 9" project=Home
python3 -m haltasks list which=today
python3 -m haltasks done task=milk
```

### Configuration

Settings live in the `[tasks]` table of `~/.config/hal/config.toml`; the vault path comes from `[hal]`:

```toml
[tasks]
vault_note = "Tasks.md"     # where the checkbox list is written, relative to the vault
remind_minutes = 10         # how long before a timed task's due time to alert
```
