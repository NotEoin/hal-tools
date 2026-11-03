# Use a pack from any harness

Each pack ships a command that serves its tools over MCP, so any harness that speaks MCP can use
them, with or without Hal.

1. Install the pack. With Hal, `hal packs add` does it. Without Hal, install from a checkout:
   the packs need `hal-kit` and `hal-hub`, which are not on PyPI yet and come from a Hal
   checkout beside this one.

   ```bash
   hal packs add hal-organiser                       # with Hal
   git clone https://github.com/NotEoin/Hal          # without Hal: Hal beside hal-tools
   git clone https://github.com/NotEoin/hal-tools
   cd hal-tools && uv tool install ./packs/organiser  # puts hal-organiser in ~/.local/bin
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
   hal-organiser call clock_timer duration=1m label=test   # runs one tool, prints the result
   ```

5. Answer approvals. A tool that asks is sent as MCP elicitation when the harness supports it.
   Otherwise it waits for `hal approve <id>` in a terminal and is denied when the timeout passes.

Checked on 2026-11-03: steps 1, 2 and 4 without Hal, from fresh clones of both repos, with
`uv tool install` into an empty tool directory and an empty home. MCP elicitation in step 5
was not tested.

An unsandboxed harness can reach your shell anyway, so these approvals are advisory there.

| Symptom | Fix |
| --- | --- |
| `hal-organiser: command not found` | Add `~/.local/bin` to `PATH`, or reinstall with `hal packs add`. |
| `Distribution not found at .../Hal/packages/hal-kit` | Clone Hal beside hal-tools (step 1). |
| Harness lists no tools | Run `hal-organiser doctor`; a bad `config.toml` stops the pack with the file and line. |
| A tool is always denied | Its tier is `system`, or it runs code; see [Tool policy](../user/policy.md). |
| An `ask` never resolves | The harness lacks elicitation; run `hal approve <id>` in a terminal. |
