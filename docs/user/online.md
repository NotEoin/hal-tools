# online

The `online` pack: web search and reading, and news feeds. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-online   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## feeds

hal-feeds keeps Hal's reading: links you save to read later, with an optional summary, and RSS or
Atom subscriptions (blogs, podcasts, YouTube channels, news) with what is new since you last looked.

### Highlights

- "Hal, save this for later": the link is stored with its title and, if asked, a short summary.
- Subscriptions to any RSS or Atom feed, polled when you ask what is new.
- Unread tracking across saved links and feed items.
- No accounts and nothing from PyPI; summaries use the local model.

### Use

Run a tool with `hal-online call feeds_<tool>`:

```bash
hal-online call feeds_subscribe url=https://hnrss.org/frontpage name="Hacker News"
hal-online call feeds_whats_new limit=5
hal-online call feeds_save url=https://example.com/article summarise=true
```

### Configuration

hal-feeds has no table of its own. Feeds are fetched under the `[net]` table described in
[web.md](#web): https only, a stored `http` feed is refused at every refresh.

## web

hal-web answers Hal's questions about the world: web search, reading and summarising pages, weather,
news, Wikipedia, definitions, unit and currency conversion, world time and exact arithmetic. Nothing
needs an API key.

### Highlights

- Search through DuckDuckGo Lite, with Bing as a fallback.
- Any page reduced to its readable text, or summarised by the local model.
- Weather now and up to 14 days ahead from Open-Meteo; place names prefer your home country.
- Headlines from any RSS or Atom feeds, filtered by topic.
- Wikipedia summaries, and definitions from the Free Dictionary API or Wiktionary.
- Units, temperatures and currencies (ECB rates through Frankfurter).
- A calculator that parses expressions itself and never runs code.

### Use

Run a tool with `hal-online call web_<tool>`:

```bash
hal-online call web_weather place=Leeds days=3
hal-online call web_search query="opening hours British Library"
hal-online call web_convert amount=100 from_unit=GBP to_unit=EUR
hal-online call web_calculate expression="15% of 80"
```

### Configuration

Settings live in the `[web]` table of `~/.config/hal/config.toml`:

```toml
[web]
home = "London"          # weather when no place is named
country = "GB"           # place names prefer this country
[web.feeds]
"BBC News" = "https://feeds.bbci.co.uk/news/rss.xml"
"Hacker News" = "https://hnrss.org/frontpage"
```

Every URL is fetched through `halkit.netguard`: https only, public addresses only, every
redirect re-checked. Those rules come from `policy.toml` `[egress]` and a pack cannot widen
them. The shared `[net]` table (web and feeds) only narrows reads:

```toml
[net]
max_bytes = 2000000      # a page or feed above this is cut
timeout_s = 20           # seconds before a fetch fails
user_agent = "Hal/0.1 (+https://github.com/NotEoin/hal-tools)"
```
