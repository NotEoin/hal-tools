# Use a pack from any harness

Each pack ships a command that serves its tools over MCP, so any harness that speaks MCP can use
them, with or without Hal.

1. Install the pack.

   ```bash
   hal packs add hal-organiser   # or uv tool install ./packs/organiser from a checkout
   ```

2. Check that it starts and see its tools.

   ```bash
   hal-organiser tools   # lists tool names, tiers and effects
   hal-organiser doctor  # checks settings and dependencies
   ```

3. Add it to the harness as a stdio MCP server whose command is `hal-organiser mcp`. The
   standalone profile applies: the `default` policy minus `system` tools.
4. Call one tool by hand to confirm the wiring.

   ```bash
   hal-organiser call clock_timer minutes=1   # runs one tool, prints the result (arguments as key=value)
   ```

5. Answer approvals. A tool that asks is sent as MCP elicitation when the harness supports it.
   Otherwise it waits for `hal approve <id>` in a terminal and is denied when the timeout passes.

Status: unverified. The `hal packs add` and `call` forms follow the CLI source and were not run
against an installed pack; step 2 shows whether they work.

An unsandboxed harness can reach your shell anyway, so these approvals are advisory there.

| Symptom | Fix |
| --- | --- |
| `hal-organiser: command not found` | Add `~/.local/bin` to `PATH`, or reinstall with `hal packs add`. |
| Harness lists no tools | Run `hal-organiser doctor`; a bad `config.toml` stops the pack with the file and line. |
| A tool is always denied | Its tier is `system`, or it runs code; see [Tool policy](../user/policy.md). |
| An `ask` never resolves | The harness lacks elicitation; run `hal approve <id>` in a terminal. |
