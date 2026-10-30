# Enable the host shell

`shell_look` runs one read-only program from a fixed table and is allowed. It reads only under
your home directory and the temporary directory, and never keys or Hal's own state. `shell_run`
runs any program; it is denied and a policy rule cannot allow it. This page widens the folders
`shell_look` may read.

1. Open the policy file.

   ```bash
   hal policy edit   # opens policy.toml in your editor
   ```

2. Add the extra folder to the tool's read roots.

   ```toml
   [tools.shell_look]
   read_roots = ["/etc", "/var/log"]   # folders shell_look may read; this replaces [paths].read_roots
   ```

3. If a root holds private checkouts, deny them.

   ```toml
   [paths]
   deny = ["~/src/private-project"]   # never readable, even inside a root
   ```

4. Check the policy and try a listing.

   ```bash
   hal policy check                    # validates policy.toml
   hal-system call shell_look command="ls /var/log" head=5   # lists five entries
   ```

Status: the root rule is covered by `packs/system/tests/test_shell.py` (a policy file with
narrow roots, and a hard-denied path inside a root). The `call` in step 4 was not run.

Run Hal in the box when you widen roots. In an unsandboxed harness the shell is reachable anyway.

| Symptom | Fix |
| --- | --- |
| `shell_run` is denied | That is fixed; use `shell_look` or a dedicated tool. |
| `shell_look` refuses a path | Add its folder in step 2; `~/.ssh` and `~/.config/hal` are always refused. |
| `shell_look` refuses a program | It is not on the table; there is no override. |
| `hal policy check` fails | It names the line; fix the TOML or the rule it rejects. |
