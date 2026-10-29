"""hal-ledger's tools: what you spend, against monthly budgets, and the subscriptions that renew.

Amounts are in the configured currency (pounds by default) and stored in pence.
Categories come from keywords ("lunch", "tesco", "uber") unless given. Bank
statement CSVs are read by finding the date, description and amount columns.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import data_dir, settings


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "ledger.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS spend (id INTEGER PRIMARY KEY, day TEXT, pence INTEGER, category TEXT, note TEXT,
            source TEXT, UNIQUE(day, pence, note, source));
        CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, pence INTEGER);
        CREATE TABLE IF NOT EXISTS subs (name TEXT PRIMARY KEY, pence INTEGER, period TEXT, next TEXT, reminded TEXT);
    """)
    return con


def _pence(amount) -> int:
    m = re.search(r"-?\d+(?:[.,]\d{1,2})?", str(amount).replace(",", ""))
    if not m:
        raise ValueError(f"cannot read the amount {amount!r}")
    return round(float(m.group(0)) * 100)


def _money(pence: int) -> str:
    return f"{settings()['symbol']}{abs(pence) / 100:,.2f}"


def categorise(note: str) -> str:
    low = note.lower()
    for cat, words in settings()["categories"].items():
        if any(re.search(rf"\b{re.escape(w)}", low) for w in words):
            return cat
    return "other"


def spend(amount: str, note: str = "", category: str = "", day: str = "") -> dict:
    """Records money spent ('12.50', note 'lunch at Pret')."""
    p = _pence(amount)
    cat = category.lower() or categorise(note)
    d = day or date.today().isoformat()
    con = _db()
    con.execute(
        "INSERT OR IGNORE INTO spend (day, pence, category, note, source) VALUES (?, ?, ?, ?, 'hal')",
        (
            d,
            p,
            cat,
            note,
        ),
    )
    con.commit()
    out = {"spent": _money(p), "category": cat}
    b = con.execute("SELECT pence FROM budgets WHERE category = ?", (cat,)).fetchone()
    if b:
        used = _month_total(con, cat)
        out["budget"] = f"{_money(used)} of {_money(b['pence'])} this month"
    return out


def _month_total(con, category: str | None = None, month: str = "") -> int:
    m = month or date.today().strftime("%Y-%m")
    sql = "SELECT COALESCE(SUM(pence), 0) FROM spend WHERE substr(day, 1, 7) = ?" + (
        " AND category = ?" if category else ""
    )
    return con.execute(sql, (m, category) if category else (m,)).fetchone()[0]


def summary(month: str = "") -> dict:
    """Spending for a month (YYYY-MM, this month by default) by category, against budgets."""
    con = _db()
    m = month or date.today().strftime("%Y-%m")
    rows = con.execute(
        """SELECT category, SUM(pence) p, COUNT(*) n FROM spend WHERE substr(day, 1, 7) = ?
                          GROUP BY category ORDER BY p DESC""",
        (m,),
    ).fetchall()
    budgets = {r["category"]: r["pence"] for r in con.execute("SELECT * FROM budgets")}
    return {
        "month": m,
        "total": _money(sum(r["p"] for r in rows)),
        "categories": [
            {
                "category": r["category"],
                "spent": _money(r["p"]),
                "items": r["n"],
                **(
                    {
                        "budget": _money(budgets[r["category"]]),
                        "over": r["p"] > budgets[r["category"]],
                    }
                    if r["category"] in budgets
                    else {}
                ),
            }
            for r in rows
        ],
    }


def recent(limit: int = 15) -> list[dict]:
    return [
        {
            "id": r["id"],
            "day": r["day"],
            "amount": _money(r["pence"]),
            "category": r["category"],
            "note": r["note"],
        }
        for r in _db().execute(
            "SELECT * FROM spend ORDER BY day DESC, id DESC LIMIT ?", (int(limit),)
        )
    ]


def budget(category: str, amount: str) -> dict:
    """Sets a monthly budget for a category."""
    con = _db()
    con.execute("INSERT OR REPLACE INTO budgets VALUES (?, ?)", (category.lower(), _pence(amount)))
    con.commit()
    return {"category": category.lower(), "monthly_budget": _money(_pence(amount))}


def subscription(name: str, amount: str, period: str = "monthly", next_payment: str = "") -> dict:
    """Records a subscription and when it next renews (YYYY-MM-DD)."""
    if period not in ("weekly", "monthly", "yearly"):
        raise ValueError("period is weekly, monthly or yearly")
    nxt = next_payment or (date.today() + timedelta(days=30)).isoformat()
    con = _db()
    con.execute(
        "INSERT OR REPLACE INTO subs VALUES (?, ?, ?, ?, NULL)", (name, _pence(amount), period, nxt)
    )
    con.commit()
    return {"subscription": name, "amount": _money(_pence(amount)), "period": period, "next": nxt}


def subscriptions() -> dict:
    rows = _db().execute("SELECT * FROM subs ORDER BY next").fetchall()
    per_month = sum(
        r["pence"] * {"weekly": 52 / 12, "monthly": 1, "yearly": 1 / 12}[r["period"]] for r in rows
    )
    return {
        "monthly_cost": _money(round(per_month)),
        "yearly_cost": _money(round(per_month * 12)),
        "subscriptions": [
            {
                "name": r["name"],
                "amount": _money(r["pence"]),
                "period": r["period"],
                "next": r["next"],
            }
            for r in rows
        ],
    }


def cancel_subscription(name: str) -> dict:
    con = _db()
    con.execute("DELETE FROM subs WHERE lower(name) = lower(?)", (name,))
    con.commit()
    return {"removed": name}


def import_csv(path: str) -> dict:
    """Imports a bank statement CSV, finding its date, description and amount columns; repeats are skipped."""
    rows = list(csv.reader(Path(path).expanduser().read_text(errors="ignore").splitlines()))
    head = [h.strip().lower() for h in rows[0]]
    col = lambda *names: next((i for i, h in enumerate(head) if any(n in h for n in names)), None)  # noqa: E731
    di, ni = col("date"), col("description", "details", "name", "payee", "reference", "merchant")
    ai, outi = col("amount", "value"), col("paid out", "debit", "money out")
    if di is None or ni is None or (ai is None and outi is None):
        raise ValueError(f"cannot find date, description and amount columns in {head}")
    con = _db()
    added = 0
    for r in rows[1:]:
        if len(r) <= max(x for x in (di, ni, ai, outi) if x is not None):
            continue
        raw = r[outi] if outi is not None and r[outi].strip() else (r[ai] if ai is not None else "")
        if not raw.strip():
            continue
        p = _pence(raw)
        if ai is not None and outi is None:
            if p >= 0:
                continue  # money in, not spending
            p = -p
        d = _date(r[di])
        cur = con.execute(
            "INSERT OR IGNORE INTO spend (day, pence, category, note, source) VALUES (?, ?, ?, ?, ?)",
            (d, p, categorise(r[ni]), r[ni].strip(), Path(path).name),
        )
        added += cur.rowcount
    con.commit()
    return {"imported": added}


def _date(text: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"cannot read the date {text!r}")


def renewals_due(days: int = 3) -> list[dict]:
    """Subscriptions renewing within N days, rolling any past date forward a period."""
    con = _db()
    today = date.today()
    out = []
    for r in con.execute("SELECT * FROM subs").fetchall():
        nxt = date.fromisoformat(r["next"])
        while nxt < today:
            nxt = {
                "weekly": nxt + timedelta(weeks=1),
                "yearly": nxt.replace(year=nxt.year + 1),
            }.get(
                r["period"], (nxt.replace(day=1) + timedelta(days=32)).replace(day=min(nxt.day, 28))
            )
        con.execute("UPDATE subs SET next = ? WHERE name = ?", (nxt.isoformat(), r["name"]))
        if (nxt - today).days <= int(days):
            out.append(
                {
                    "name": r["name"],
                    "amount": _money(r["pence"]),
                    "on": nxt.isoformat(),
                    "reminded": r["reminded"],
                }
            )
    con.commit()
    return out
