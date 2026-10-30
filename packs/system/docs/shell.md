# hal-shell

hal-shell is Hal's fallback for anything the other modules do not cover: it runs shell commands.
`shell_look` runs one read-only program from a fixed table; `shell_run` is denied by default and the
hub asks you before every run.

## Highlights

- `shell_look` starts no shell. The command is split, the program must be on the table (`ls`, `cat`,
  `grep`, `find`, `df`, `ps`, `systemctl status`, `journalctl` and about fifty more), every option
  and argument must be allowed for that program, and it runs as an argv list from `/usr/bin`,
  `/bin`, `/usr/sbin` or `/sbin`.
- Pipes, redirects, chaining and substitution are refused. Use the `filter` argument to keep matching
  lines and `head` to keep the first lines.
- Every path argument and `cwd` is resolved (symlinks followed) and must be inside your home
  directory or `/tmp`, and outside `~/.ssh`, `~/.gnupg`, Hal's own config and state, `/proc`, `/sys`
  and `/dev`.
- The child runs in its own process group with no stdin and a minimal environment. Output is read up
  to `max_output` bytes, and the group is killed on a timeout or an overflow.
- `shell_run` runs any one program, also without a shell: `|`, `>` and `$VAR` reach the program as
  literal arguments. Its timeout is capped at `max_timeout_s`.

## Install

hal-shell needs Python 3.11 or later and bash.

```bash
git clone <url> ~/src/hal-ecosystem/hal-shell
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub shell_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-shell
python3 -m halshell look command="du -sh --max-depth=1 ~/Downloads" head=20
hal-hub shell_run command="mkdir -p ~/projects/new" --yes
```

## Configuration

Settings live in the `[shell]` table of `~/.config/hal/config.toml`:

```toml
[shell]
timeout_s = 20         # seconds a shell_look command may run
max_output = 65536     # bytes of output read
max_timeout_s = 600    # upper bound for a shell_run timeout
```

## Licence

MIT. See [LICENSE](LICENSE).
