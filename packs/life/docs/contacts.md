# hal-contacts

hal-contacts keeps the people in your life as notes in your Obsidian vault: contact details,
birthdays, how you know them, and a dated log of when you spoke and what about. Hal can tell you
whose birthday is coming and who you have not caught up with in a while.

## Highlights

- One note per person in the vault's `People/` folder, so the same notes are linked and searched by hal-memory.
- Birthdays in plain words ("3 March"), added to the calendar as a yearly event through hal-hub.
- An interaction log: "had lunch with Sam, she's moving to Leeds" is dated and kept.
- Upcoming birthdays with ages, and people you have not been in touch with for N days.
- vCard import from a phone, Google Contacts or iCloud.

## Install

hal-contacts needs Python 3.11 or later and an Obsidian vault (any folder of Markdown works).

```bash
git clone <url> ~/src/hal-ecosystem/hal-contacts
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub contacts_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-contacts
python3 -m halcontacts add name="Sam Lee" birthday="3 March" relationship="friend from uni"
python3 -m halcontacts log name=Sam note="lunch, she's moving to Leeds"
python3 -m halcontacts birthdays days=30
python3 -m halcontacts import path=~/Downloads/contacts.vcf
```

## Configuration

The vault comes from `[hal].vault`; the `[contacts]` table sets the folder:

```toml
[contacts]
folder = "People"
```

## Licence

MIT. See [LICENSE](LICENSE).
