"""Daily check: alerts about subscriptions renewing in the next three days, once per renewal.

python -m halledger.remind      (run by the systemd timer)
"""

from halkit.notify import send

from . import tools


def main() -> None:
    con = tools._db()
    for s in tools.renewals_due(3):
        if s["reminded"] != s["on"]:
            send(
                f"{s['name']} renews {s['on']}",
                f"{s['amount']} will be taken. Cancel before then if you no longer use it.",
                source="ledger",
            )
            con.execute("UPDATE subs SET reminded = ? WHERE name = ?", (s["on"], s["name"]))
    con.commit()


if __name__ == "__main__":
    main()
