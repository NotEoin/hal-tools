# hal-tasks

hal-tasks is Hal's to-do list: tasks in plain English with due dates, priorities, projects and
repeats, reminders when a timed task falls due, and a note in your Obsidian vault where ticking a box
marks the task done.

## Highlights

- "Buy milk tomorrow", "water the plants every monday at 9": due dates and repeats read from the words.
- Completing a repeating task schedules the next one.
- Lists for today (due today or earlier), overdue, upcoming, done this week, by project or tag.
- A morning alert with the day's tasks, and a reminder before each timed task, through hal-notify.
- `Tasks.md` in the vault lists open tasks by project as checkboxes; tick one in Obsidian and Hal
  marks it done.

## Install

hal-tasks needs Python 3.11 or later and nothing from PyPI.

```bash
git clone <url> ~/src/hal-ecosystem/hal-tasks
ln -s ~/src/hal-ecosystem/hal-tasks/systemd/hal-tasks-reminders.service ~/.config/systemd/user/
systemctl --user enable --now hal-tasks-reminders.service
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub tasks_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-tasks
python3 -m haltasks add title="Buy milk tomorrow"
python3 -m haltasks add title="Water the plants" due="every monday at 9" project=Home
python3 -m haltasks list which=today
python3 -m haltasks done task=milk
```

## Configuration

Settings live in the `[tasks]` table of `~/.config/hal/config.toml`; the vault path comes from `[hal]`:

```toml
[tasks]
vault_note = "Tasks.md"     # where the checkbox list is written, relative to the vault
remind_minutes = 10         # how long before a timed task's due time to alert
```

## Licence

MIT. See [LICENSE](LICENSE).
