# Tool policy

Every tool declares a tier and its effects in its manifest. The hub decides from those, not from
the tool's own claims. The full per-tool table is `tests/tool-policy.csv`; a test keeps it equal
to the manifests.

## Tiers and defaults

| Tier | Meaning | Default under the `default` profile |
| --- | --- | --- |
| `read` | Looks at something, changes nothing | allow |
| `write` | Changes data Hal keeps (calendar, tasks, notes) | allow, except destructive ones, which ask |
| `act` | Does something on the machine or the network | allow when reversible, else ask; code runners deny |
| `send` | Sends something to another person or service | ask, except `notify_send`, `briefing_deliver` and `calendar_sync`, whose destinations are fixed in config |
| `system` | Power, packages, devices | ask, never allow |

`shell_run` and `dev_run_tests` run code and are denied. `calendar_delete`, `tasks_delete`,
`habits_remove` and the `screen_*` tools ask, because they destroy data or can show passwords.

## Change a decision

Decisions are made by the user on the host, never by a tool call. Edit `[policy]` in
`~/.config/hal/config.toml`, or answer an approval prompt once with `hal approve <id>`.

## Standalone use and approvals

`hal-<pack> mcp` uses the `standalone` profile: the `default` profile without `system` tools. An
`ask` is sent as MCP elicitation when the client supports it, otherwise it waits for
`hal approve <id>` and becomes a deny when the approval timeout passes.

An unsandboxed harness can reach your shell anyway, so these approvals are advisory there. Run the
harness in the box if you need them to hold.

## Paths and addresses

A parameter that names a file must declare `format = "path"` with an access mode; the hub applies
its path rule before the tool runs. A tool may narrow that further with its own roots
(`[files].roots`, `[dev].roots`, `[calendar].import_roots`), never widen it. Web and feed fetches go
through the `[egress]` rules.
