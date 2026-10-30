# Add a mail account

Hal ships with no mail account. Every mail tool fails until one is configured.

1. Create an app password at your mail provider (not your login password).
2. Save it in a file only you can read.

   ```bash
   printf '%s' 'abcd efgh ijkl mnop' > ~/.config/hal/mail-personal   # the app password
   chmod 600 ~/.config/hal/mail-personal                              # owner only
   ```

3. Add the account to `~/.config/hal/config.toml`.

   ```toml
   [mail.accounts.personal]
   address = "you@example.org"
   imap = "imap.example.org"
   smtp = "smtp.example.org"
   password_file = "~/.config/hal/mail-personal"
   ```

   With one account, `[mail] default` can stay empty. With several, set `default = "personal"`.
4. Check it.

   ```bash
   hal-comms call mail_accounts   # lists the configured accounts, never the password
   ```

| Symptom | Fix |
| --- | --- |
| `no mail account configured` | Add `[mail.accounts.<name>]` as in step 3. |
| Login refused | Use an app password, and check the `imap` host. |
| `password_file` not found | Fix the path; it must exist and be readable by you. |
| Sending asks every time | `send` tools ask by default; answer once or see [Tool policy](../user/policy.md). |
