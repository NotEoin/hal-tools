# Allow a website for web_read

`web_read` fetches public https pages through the egress rules. A site outside them is refused.

1. Read the refusal. It names the host that was blocked.
2. Add the host to the tool's rule.

   ```bash
   hal policy allow web_read --domain docs.example.org   # appends the host to [tools.web_read]
   ```

   The result in `policy.toml`:

   ```toml
   [tools.web_read]
   domains = ["docs.example.org"]   # lowercase host, or "*.example.org"
   ```
3. Try the page again.

   ```bash
   hal-online call web_read url=https://docs.example.org/   # fetches and prints the page text
   ```

A pack cannot widen the egress rules by itself, and private addresses stay blocked. A LAN service
needs `[egress].allow_private`.

| Symptom | Fix |
| --- | --- |
| The fetch names a blocked host | Add the host as in step 2. |
| Only `http://` works for that site | Not supported; the fetch is https only. |
| A redirect is refused | The target host is checked too; allow it as well. |
| The page is cut short | Raise `[net].max_bytes`; the default is 2000000. |
