# Security

## Reporting

Report a vulnerability privately through GitHub security advisories on this repository. Do not open
a public issue. Include the pack, the tool, the steps to reproduce and what an attacker gains.

## Model

Treat the model as hostile. A tool must be safe to call with any argument a model can write.

- Tiers and effects come from the manifest and are enforced by the hub; see
  [docs/user/policy.md](docs/user/policy.md).
- File parameters are checked against allowed roots before the tool runs; a tool may narrow them.
- Fetches go through `halkit.netguard` and the `[egress]` rules.
- Subprocesses take an argv list and a timeout. No tool uses a shell string.
- Secrets live in files beside the config, owner-only, and are never returned by a tool.
- No tool calls Claude Code by default.

## Limits

An unsandboxed harness can reach your shell anyway, so approvals there are advisory. Run Hal in the
box for containment.
