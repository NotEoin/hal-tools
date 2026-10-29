# hal-web

hal-web answers Hal's questions about the world: web search, reading and summarising pages, weather,
news, Wikipedia, definitions, unit and currency conversion, world time and exact arithmetic. Nothing
needs an API key.

## Highlights

- Search through DuckDuckGo Lite, with Bing as a fallback.
- Any page reduced to its readable text, or summarised by the local model.
- Weather now and up to 14 days ahead from Open-Meteo; place names prefer your home country.
- Headlines from any RSS or Atom feeds, filtered by topic.
- Wikipedia summaries, and definitions from the Free Dictionary API or Wiktionary.
- Units, temperatures and currencies (ECB rates through Frankfurter).
- A calculator that parses expressions itself and never runs code.

## Install

hal-web needs Python 3.11 or later and an internet connection; page summaries need Ollama.

```bash
git clone <url> ~/src/hal-ecosystem/hal-web
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub web_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-web
python3 -m halweb weather place=Leeds days=3
python3 -m halweb search query="opening hours British Library"
python3 -m halweb convert amount=100 from_unit=GBP to_unit=EUR
python3 -m halweb calculate expression="15% of 80"
```

## Configuration

Settings live in the `[web]` table of `~/.config/hal/config.toml`:

```toml
[web]
home = "London"          # weather when no place is named
country = "GB"           # place names prefer this country
[web.feeds]
"BBC News" = "https://feeds.bbci.co.uk/news/rss.xml"
"Hacker News" = "https://hnrss.org/frontpage"
```

## Licence

MIT. See [LICENSE](LICENSE).
