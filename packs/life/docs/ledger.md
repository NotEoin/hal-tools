# hal-ledger

hal-ledger keeps track of money: tell Hal what you spent and it is categorised and counted against
your monthly budgets; subscriptions are listed with their yearly cost and you are reminded before
each renews; bank statement CSVs are imported in one go.

## Highlights

- "12.50 lunch at Pret": amount and note in, category worked out from keywords.
- Monthly budgets per category, with the running total each time you spend.
- Monthly summaries by category, marking any budget that is over.
- Subscriptions with their monthly and yearly cost, and an alert three days before each renewal.
- Bank statement CSV import that finds the columns itself, skips money in and never double-counts.

## Install

hal-ledger needs Python 3.11 or later.

```bash
git clone <url> ~/src/hal-ecosystem/hal-ledger
ln -s ~/src/hal-ecosystem/hal-ledger/systemd/* ~/.config/systemd/user/
systemctl --user enable --now hal-ledger-remind.timer
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub ledger_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-ledger
python3 -m halledger spend amount=12.50 note="lunch at Pret"
python3 -m halledger budget category="eating out" amount=150
python3 -m halledger subscription name=Spotify amount=11.99 period=monthly next_payment=2026-11-02
python3 -m halledger import path=~/Downloads/statement.csv
```

## Configuration

Settings live in the `[ledger]` table of `~/.config/hal/config.toml`:

```toml
[ledger]
symbol = "\u00a3"   # the pound sign
[ledger.categories]
pets = ["vet", "pets at home"]
```

## Licence

MIT. See [LICENSE](LICENSE).
