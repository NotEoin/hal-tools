"""hal-web's tools: answers from the internet and a few things worked out locally.

Search uses DuckDuckGo's HTML page; weather Open-Meteo; currency the ECB rates
through Frankfurter; definitions dictionaryapi.dev; encyclopaedia Wikipedia's
REST API; news any RSS or Atom feeds. None needs an API key. Maths is a safe
expression evaluator, never eval().
"""

from __future__ import annotations

import ast
import html
import json
import math
import operator
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo, available_timezones

from hal_online import net

from . import llm
from .settings import settings

_get = net.get


def _json(url: str) -> dict | list:
    return json.loads(_get(url))


# -- search and pages -------------------------------------------------------------


def search(query: str, limit: int = 6) -> list[dict]:
    """Web search results: title, link and snippet (DuckDuckGo Lite, then Bing)."""
    q = urllib.parse.quote_plus(query)
    out = []
    try:
        page = _get(f"https://lite.duckduckgo.com/lite/?q={q}").decode(errors="ignore")
        links = re.findall(
            r"<a rel=\"nofollow\" href=\"([^\"]+)\" class='result-link'>(.*?)</a>", page, re.S
        )
        snippets = re.findall(r"<td class='result-snippet'>(.*?)</td>", page, re.S)
        for (href, title), snip in zip(links, snippets + [""] * len(links), strict=False):
            target = urllib.parse.parse_qs(urllib.parse.urlparse(html.unescape(href)).query).get(
                "uddg", [href]
            )[0]
            out.append({"title": _strip(title), "url": target, "snippet": _strip(snip)})
    except OSError:
        pass
    if not out:
        page = _get(f"https://www.bing.com/search?q={q}&setlang=en-GB").decode(errors="ignore")
        for block in page.split('class="b_algo"')[1:]:
            m = re.search(r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
            if m:
                snip = re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
                out.append(
                    {
                        "title": _strip(m.group(2)),
                        "url": html.unescape(m.group(1)),
                        "snippet": _strip(snip.group(1)) if snip else "",
                    }
                )
    return out[: int(limit)]


def _strip(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


class _Text(HTMLParser):
    SKIP = frozenset(
        {"script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"}
    )

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.depth:
            self.parts.append(data)


def read_page(url: str, summarise: bool = False, limit: int = 6000) -> dict:
    """The readable text of a web page, or a short summary of it from the local model."""
    p = _Text()
    response = net.fetch(url)
    p.feed(response.body.decode(errors="ignore"))
    text = re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", "".join(p.parts))).strip()
    out = {"url": url, "title": p.title.strip()}
    if response.truncated:
        out["note"] = "the page was cut at the read cap, so the text is partial"
    if summarise:
        out["summary"] = llm.chat(
            "Summarise this web page in at most 120 words of plain prose. Use only the page.",
            text[:12000],
        ).strip()
    else:
        out["text"] = text[: int(limit)]
    return out


# -- weather ------------------------------------------------------------------------

CODES = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _place(place: str) -> dict:
    name = place or settings()["home"]
    hits = _json(
        "https://geocoding-api.open-meteo.com/v1/search?count=10&language=en&name="
        + urllib.parse.quote(name)
    ).get("results")
    if not hits:
        raise ValueError(f"cannot find the place {name!r}")
    # A place name means the one in the home country unless a country is named.
    home = settings()["country"]
    return next((h for h in hits if h.get("country_code") == home), hits[0])


def weather(place: str = "", days: int = 3) -> dict:
    """Current weather and a daily forecast for a place (home by default)."""
    loc = _place(place)
    q = urllib.parse.urlencode(
        {
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "timezone": "auto",
            "current": (
                "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,"
                "relative_humidity_2m,precipitation"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,sunrise,sunset"
            ),
            "forecast_days": max(1, min(14, int(days))),
        }
    )
    d = _json("https://api.open-meteo.com/v1/forecast?" + q)
    cur = d["current"]
    daily = d["daily"]
    return {
        "place": f"{loc['name']}, {loc.get('country', '')}",
        "now": {
            "temperature_c": cur["temperature_2m"],
            "feels_like_c": cur["apparent_temperature"],
            "sky": CODES.get(cur["weather_code"], "unknown"),
            "wind_kmh": cur["wind_speed_10m"],
            "humidity": cur["relative_humidity_2m"],
            "rain_mm": cur["precipitation"],
        },
        "days": [
            {
                "date": daily["time"][i],
                "sky": CODES.get(daily["weather_code"][i], "unknown"),
                "high_c": daily["temperature_2m_max"][i],
                "low_c": daily["temperature_2m_min"][i],
                "rain_chance": daily["precipitation_probability_max"][i],
                "sunrise": daily["sunrise"][i][11:],
                "sunset": daily["sunset"][i][11:],
            }
            for i in range(len(daily["time"]))
        ],
    }


# -- reference ----------------------------------------------------------------------


def wikipedia(topic: str) -> dict:
    """A short encyclopaedia summary of a topic."""
    title = urllib.parse.quote(topic.strip().replace(" ", "_"))
    try:
        d = _json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}?redirect=true")
    except net.HTTPStatusError as err:
        hits = _json(
            "https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&format=json&search="
            + urllib.parse.quote(topic)
        )
        if not hits[1]:
            raise ValueError(f"Wikipedia has nothing on {topic!r}") from err
        d = _json(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(hits[1][0].replace(" ", "_"))
        )
    return {
        "title": d.get("title"),
        "summary": d.get("extract"),
        "url": d.get("content_urls", {}).get("desktop", {}).get("page"),
    }


def define(word: str) -> dict:
    """Dictionary definitions of an English word (Free Dictionary API, then Wiktionary)."""
    try:
        d = _json(
            "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word.strip())
        )
    except OSError:
        return _wiktionary(word)
    meanings = []
    for m in d[0].get("meanings", [])[:3]:
        for df in m.get("definitions", [])[:2]:
            meanings.append(
                {
                    "part": m.get("partOfSpeech"),
                    "definition": df.get("definition"),
                    "example": df.get("example"),
                }
            )
    return {"word": d[0].get("word"), "phonetic": d[0].get("phonetic"), "meanings": meanings}


def _wiktionary(word: str) -> dict:
    try:
        d = _json(
            "https://en.wiktionary.org/api/rest_v1/page/definition/"
            + urllib.parse.quote(word.strip())
        )
    except OSError:
        raise ValueError(f"no definition found for {word!r}") from None
    meanings = [
        {
            "part": e.get("partOfSpeech"),
            "definition": _strip(df.get("definition", "")),
            "example": None,
        }
        for e in d.get("en", [])[:3]
        for df in e.get("definitions", [])[:2]
        if df.get("definition")
    ]
    if not meanings:
        raise ValueError(f"no definition found for {word!r}")
    return {"word": word, "phonetic": None, "meanings": meanings}


def news(topic: str = "", limit: int = 8) -> list[dict]:
    """Latest headlines from the configured feeds, optionally only those mentioning a topic."""
    items = []
    for name, url in settings()["feeds"].items():
        try:
            root = net.parse_xml(_get(url))
        except (OSError, ValueError, ET.ParseError):  # ValueError: BlockedURL
            continue
        for it in root.iter():
            if it.tag.split("}")[-1] not in ("item", "entry"):
                continue

            def get(name: str, it: ET.Element = it) -> str:
                for child in it:
                    if child.tag.split("}")[-1] == name:
                        return child.text or child.get("href") or ""
                return ""

            title, summary = (
                (get("title") or "").strip(),
                _strip(get("description") or get("summary") or ""),
            )
            if topic and topic.lower() not in f"{title} {summary}".lower():
                continue
            items.append(
                {"source": name, "title": title, "summary": summary[:240], "link": get("link")}
            )
    return items[: int(limit)]


# -- conversions and maths -----------------------------------------------------------

UNITS = {  # to SI base unit
    "length": {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1,
        "km": 1000,
        "in": 0.0254,
        "inch": 0.0254,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
        "yd": 0.9144,
        "yard": 0.9144,
        "mile": 1609.344,
        "mi": 1609.344,
    },
    "mass": {
        "mg": 1e-6,
        "g": 0.001,
        "kg": 1,
        "tonne": 1000,
        "oz": 0.028349523,
        "ounce": 0.028349523,
        "lb": 0.45359237,
        "pound": 0.45359237,
        "stone": 6.35029318,
        "st": 6.35029318,
    },
    "volume": {
        "ml": 0.001,
        "l": 1,
        "litre": 1,
        "liter": 1,
        "pint": 0.56826125,
        "gallon": 4.54609,
        "cup": 0.25,
        "tsp": 0.005,
        "tbsp": 0.015,
        "floz": 0.0284130625,
    },
    "speed": {"mph": 0.44704, "kmh": 0.2777778, "kph": 0.2777778, "ms": 1, "knot": 0.514444},
    "data": {
        "b": 1,
        "kb": 1e3,
        "mb": 1e6,
        "gb": 1e9,
        "tb": 1e12,
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
    },
    "time": {
        "s": 1,
        "sec": 1,
        "second": 1,
        "min": 60,
        "minute": 60,
        "h": 3600,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
    },
}


def _unit(u: str) -> tuple[str, float] | None:
    u = u.lower().rstrip(".")
    for cand in (u, u.rstrip("s"), u.removesuffix("es")):
        for kind, table in UNITS.items():
            if cand in table:
                return kind, table[cand]
    return None


def convert(amount: float, from_unit: str, to_unit: str) -> dict:
    """Converts between units, temperatures and currencies."""
    a, f, t = float(amount), from_unit.strip(), to_unit.strip()
    temps = {"c": "c", "celsius": "c", "f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}
    if f.lower() in temps and t.lower() in temps:
        c = {"c": a, "f": (a - 32) * 5 / 9, "k": a - 273.15}[temps[f.lower()]]
        val = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[temps[t.lower()]]
        return {"result": round(val, 2), "unit": t}
    uf, ut = _unit(f), _unit(t)
    if uf and ut:
        if uf[0] != ut[0]:
            raise ValueError(f"cannot convert {uf[0]} to {ut[0]}")
        return {"result": round(a * uf[1] / ut[1], 6), "unit": t}
    if re.fullmatch(r"[A-Za-z]{3}", f) and re.fullmatch(r"[A-Za-z]{3}", t):
        d = _json(f"https://api.frankfurter.app/latest?amount={a}&from={f.upper()}&to={t.upper()}")
        return {"result": d["rates"][t.upper()], "unit": t.upper(), "rate_date": d["date"]}
    raise ValueError(f"cannot convert {from_unit} to {to_unit}")


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
FUNCS = {
    n: getattr(math, n)
    for n in (
        "sqrt",
        "sin",
        "cos",
        "tan",
        "log",
        "log10",
        "log2",
        "exp",
        "floor",
        "ceil",
        "factorial",
        "radians",
        "degrees",
        "asin",
        "acos",
        "atan",
    )
}
FUNCS.update(abs=abs, round=round, pi=math.pi, e=math.e)


MAX_FACTORIAL_ARG = 1000  # factorial(1000) has 2568 digits and is computed in microseconds
MAX_EXPONENT = 1000
MAX_INT_BITS = 3322  # 10**1000 is just under 2**3322; larger integers are refused
POW_BITS_BUDGET = MAX_INT_BITS  # skips a power that surely exceeds it, before computing it


def _bounded(value):
    """Returns `value`, or raises `ValueError` for an integer above 10**1000."""
    if isinstance(value, int) and value.bit_length() > MAX_INT_BITS:
        raise ValueError("result too large")
    return value


def calculate(expression: str) -> dict:
    """Works out arithmetic: + - * / ** % and functions such as sqrt, log and sin."""
    expr = (
        expression.replace("^", "**").replace("x", "*")
        if re.fullmatch(r"[\d\s.x^()+\-*/]+", expression)
        else expression
    )
    expr = re.sub(r"(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)", r"(\1/100*\2)", expr)

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > MAX_EXPONENT:
                    raise ValueError("exponent too large")
                if (
                    isinstance(left, int)
                    and right > 0
                    and (left.bit_length() - 1) * right > POW_BITS_BUDGET
                ):
                    raise ValueError("result too large")
            try:
                return _bounded(OPS[type(node.op)](left, right))
            except OverflowError as exc:
                raise ValueError("result too large") from exc
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Name) and node.id in FUNCS and not callable(FUNCS[node.id]):
            return FUNCS[node.id]
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and callable(FUNCS.get(node.func.id))
        ):
            args = [ev(a) for a in node.args]
            if node.func.id == "factorial" and args and abs(args[0]) > MAX_FACTORIAL_ARG:
                raise ValueError("factorial argument too large")
            try:
                return _bounded(FUNCS[node.func.id](*args))
            except OverflowError as exc:
                raise ValueError("result too large") from exc
        raise ValueError(f"not allowed in a calculation: {ast.dump(node)[:60]}")

    value = ev(ast.parse(expr, mode="eval"))
    return {
        "expression": expression,
        "result": round(value, 10) if isinstance(value, float) else value,
    }


def _spoken(now) -> str:
    """Returns the time as it is said ("8:29 pm"), so a model never converts 24-hour time itself."""
    return f"{now.hour % 12 or 12}:{now:%M} {'am' if now.hour < 12 else 'pm'}"


def world_time(place: str = "") -> dict:
    """The time now in a city or time zone (or here)."""
    if not place:
        now = datetime.now().astimezone()
        return {
            "place": "here",
            "time": now.strftime("%H:%M"),
            "spoken": _spoken(now),
            "date": now.strftime("%A %-d %B"),
        }
    zone = next(
        (
            z
            for z in available_timezones()
            if z.lower().endswith("/" + place.lower().replace(" ", "_"))
        ),
        None,
    )
    offset = None
    if zone is None:
        loc = _place(place)
        d = _json(
            f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}"
            "&timezone=auto&current=temperature_2m"
        )
        zone, offset = d["timezone"], d["utc_offset_seconds"]
    try:
        now = datetime.now(ZoneInfo(zone))
    except Exception:  # noqa: BLE001 - some Pythons ship without the zone database; use the live offset
        if offset is None:
            loc = _place(place)
            offset = _json(
                f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}"
                f"&longitude={loc['longitude']}&timezone=auto&current=temperature_2m"
            )["utc_offset_seconds"]
        from datetime import timedelta, timezone

        now = datetime.now(timezone(timedelta(seconds=offset)))
    return {
        "place": place,
        "zone": zone,
        "time": now.strftime("%H:%M"),
        "spoken": _spoken(now),
        "date": now.strftime("%A %-d %B"),
        "utc_offset": now.strftime("%z"),
    }
