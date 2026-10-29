# hal-dev

hal-dev tells Hal about your code: every git repository's branch, uncommitted work and unpushed
commits, recent history and changes, TODO comments, whether the tests pass, and your GitHub pull
requests and issues.

## Highlights

- Finds every repository under the configured folders, skipping virtual environments and vendored code.
- Uncommitted files, commits ahead or behind the upstream, and the last commit, in one call.
- TODO, FIXME, HACK and XXX comments in tracked files.
- Runs a project's tests with npm, cargo, pytest or unittest, whichever it uses.
- GitHub pull requests, issues and notifications through the `gh` command.
- Reads only: it never commits, pushes or switches branches.

## Install

hal-dev needs Python 3.11 or later and git; GitHub features need `gh` with `gh auth login`.

```bash
git clone <url> ~/src/hal-ecosystem/hal-dev
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub dev_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-dev
python3 -m haldev repos dirty_only=true
python3 -m haldev run_tests repo=hal-hub
python3 -m haldev todos repo=hatch
```

## Configuration

Settings live in the `[dev]` table of `~/.config/hal/config.toml`:

```toml
[dev]
roots = ["~/src", "~/code"]   # where repositories are looked for
depth = 2                                 # how many folders deep
```

## Licence

MIT. See [LICENSE](LICENSE).
