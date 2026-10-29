# hal-shell

hal-shell is Hal's fallback for anything the other modules do not cover: it runs shell commands.
Commands that only read run straight away; anything that could change the system runs only after you
confirm.

## Highlights

- `shell_look` runs read-only commands and pipelines (`ls`, `grep`, `df`, `ps`, `git log`, `journalctl`
  and about seventy others) with no confirmation.
- Every command in a pipeline is checked, with the subcommands that write refused (`git push`,
  `systemctl stop`, `apt install`, `find -delete`, `sed -i`), along with redirection to files,
  chaining, command substitution, background jobs, and awk or sed scripts that run programs.
- `shell_run` runs anything, and hal-hub asks you first.
- Output is cut to a readable length.

## Install

hal-shell needs Python 3.11 or later and bash.

```bash
git clone <url> ~/src/hal-ecosystem/hal-shell
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub shell_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-shell
python3 -m halshell look command="du -sh ~/Downloads/* | sort -h | tail -5"
hal-hub shell_run command="mkdir -p ~/projects/new" --yes
```

## Configuration

Settings live in the `[shell]` table of `~/.config/hal/config.toml`:

```toml
[shell]
max_output = 12000     # characters of output returned
```

## Licence

MIT. See [LICENSE](LICENSE).
