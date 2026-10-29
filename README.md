# hal-tools

Small tool extensions for [Hal](https://github.com/NotEoin/Hal), grouped into eight packs:
`organiser`, `life`, `comms`, `online`, `desktop`, `system`, `work` and `jobs`.

Status: work in progress. The history of 29 earlier extension repositories is imported under
`packs/<pack>/`, and the packs are being ported to the Hal 0.1 interfaces.

## Test

```bash
uv sync --all-packages   # needs hal-kit and hal-hub in ../Hal.next
uv run pytest            # hermetic tests only
```

## Licence

MIT, see `LICENSE`.
