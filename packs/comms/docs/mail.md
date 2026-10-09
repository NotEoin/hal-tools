# hal-mail

hal-mail lets Hal read your email over IMAP: what is unread, a search, any message in full, and a
short summary of what needs a reply. It saves replies to your Drafts folder, and sends only when you
confirm.

## Highlights

- Read-only by default: mailboxes are opened with EXAMINE and messages fetched with BODY.PEEK, so
  nothing is marked read, moved or deleted.
- Several accounts, any IMAP provider; Gmail works with an app password.
- HTML mail reduced to plain text; encoded and folded headers decoded.
- Summaries of the unread mail from the local model.
- Drafts appended to the Drafts folder for you to check; sending through SMTP asks for confirmation.

## Install

hal-mail needs Python 3.11 or later and an app password for each account (Gmail: Google Account,
Security, App passwords), saved in a file only you can read:

```bash
git clone <url> ~/src/hal-ecosystem/hal-mail
printf '%s' 'abcd efgh ijkl mnop' > ~/.config/hal/mail-personal && chmod 600 ~/.config/hal/mail-personal
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub mail_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-mail
python3 -m halmail unread limit=5
python3 -m halmail search query="interview" days=14
python3 -m halmail summarise
```

## Configuration

Accounts live in the `[mail]` table of `~/.config/hal/config.toml`:

```toml
[mail]
default = "personal"
[mail.accounts.personal]
address = "you@gmail.com"
imap = "imap.gmail.com"
smtp = "smtp.gmail.com"
password_file = "~/.config/hal/mail-personal"
```

## Licence

MIT. See [LICENSE](LICENSE).
