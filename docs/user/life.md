# life

The `life` pack: contacts, habits and the ledger. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-life   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## contacts

hal-contacts keeps the people in your life as notes in your Obsidian vault: contact details,
birthdays, how you know them, and a dated log of when you spoke and what about. Hal can tell you
whose birthday is coming and who you have not caught up with in a while.

### Highlights

- One note per person in the vault's `People/` folder, so the same notes are linked and searched by hal-memory.
- Birthdays in plain words ("3 March"), added to the calendar as a yearly event through hal-hub.
- An interaction log: "had lunch with Sam, she's moving to Leeds" is dated and kept.
- Upcoming birthdays with ages, and people you have not been in touch with for N days.
- vCard import from a phone, Google Contacts or iCloud.

### Use

Run a tool with `hal-life call contacts_<tool>`:

```bash
hal-life call contacts_add name="Sam Lee" birthday="3 March" relationship="friend from uni"
hal-life call contacts_log name=Sam note="lunch, she's moving to Leeds"
hal-life call contacts_birthdays days=30
hal-life call contacts_import path=~/Downloads/contacts.vcf
```

### Configuration

The vault comes from `[hal].vault`; the `[contacts]` table sets the folder:

```toml
[contacts]
folder = "People"
```

## habits

hal-habits tracks the small things: habits with a daily target and a streak (water, exercise,
reading, medication), how you feel, and how you slept. Tell Hal "I drank a glass of water" or "I
slept seven hours" and it is logged; an evening nudge lists what is still to do.

### Highlights

- Habits with daily targets in any unit, and streaks of days that met the target.
- Mood from 1 to 5 with notes, and sleep hours with quality.
- A seven-day view of habits met, mood and sleep.
- An evening nudge at 20:00 through hal-notify for habits not yet done.

### Use

Run a tool with `hal-life call habits_<tool>`:

```bash
hal-life call habits_create name=water target=8 unit=glasses
hal-life call habits_log name=water
hal-life call habits_mood score=4 note="good run"
hal-life call habits_week
```

### Configuration

hal-habits has no settings; change the nudge time in `systemd/hal-habits-nudge.timer`.

## ledger

hal-ledger keeps track of money: tell Hal what you spent and it is categorised and counted against
your monthly budgets; subscriptions are listed with their yearly cost and you are reminded before
each renews; bank statement CSVs are imported in one go.

### Highlights

- "12.50 lunch at Pret": amount and note in, category worked out from keywords.
- Monthly budgets per category, with the running total each time you spend.
- Monthly summaries by category, marking any budget that is over.
- Subscriptions with their monthly and yearly cost, and an alert three days before each renewal.
- Bank statement CSV import that finds the columns itself, skips money in and never double-counts.

### Use

Run a tool with `hal-life call ledger_<tool>`:

```bash
hal-life call ledger_spend amount=12.50 note="lunch at Pret"
hal-life call ledger_budget category="eating out" amount=150
hal-life call ledger_subscription name=Spotify amount=11.99 period=monthly next_payment=2026-11-02
hal-life call ledger_import path=~/Downloads/statement.csv
```

### Configuration

Settings live in the `[ledger]` table of `~/.config/hal/config.toml`:

```toml
[ledger]
symbol = "\u00a3"   # the pound sign
[ledger.categories]
pets = ["vet", "pets at home"]
```
