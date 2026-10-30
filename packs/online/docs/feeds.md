# hal-feeds

hal-feeds keeps Hal's reading: links you save to read later, with an optional summary, and RSS or
Atom subscriptions (blogs, podcasts, YouTube channels, news) with what is new since you last looked.

## Highlights

- "Hal, save this for later": the link is stored with its title and, if asked, a short summary.
- Subscriptions to any RSS or Atom feed, polled when you ask what is new.
- Unread tracking across saved links and feed items.
- No accounts and nothing from PyPI; summaries use the local model.

## Install

hal-feeds needs Python 3.11 or later; summaries need Ollama.

```bash
git clone <url> ~/src/hal-ecosystem/hal-feeds
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub feeds_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-feeds
python3 -m halfeeds subscribe url=https://hnrss.org/frontpage name="Hacker News"
python3 -m halfeeds whats_new limit=5
python3 -m halfeeds save url=https://example.com/article summarise=true
```

## Configuration

hal-feeds has no table of its own. Feeds are fetched under the `[net]` table described in
[web.md](web.md): https only, a stored `http` feed is refused at every refresh.

## Licence

MIT. See [LICENSE](LICENSE).
