# comms

The `comms` pack: mail, phone and Telegram. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-comms   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## mail

hal-mail lets Hal read your email over IMAP: what is unread, a search, any message in full, and a
short summary of what needs a reply. It saves replies to your Drafts folder, and sends only when you
confirm.

### Highlights

- Read-only by default: mailboxes are opened with EXAMINE and messages fetched with BODY.PEEK, so
  nothing is marked read, moved or deleted.
- Several accounts, any IMAP provider; Gmail works with an app password.
- HTML mail reduced to plain text; encoded and folded headers decoded.
- Summaries of the unread mail from the local model.
- Drafts appended to the Drafts folder for you to check; sending through SMTP asks for confirmation.

### Use

Run a tool with `hal-comms call mail_<tool>`:

```bash
hal-comms call mail_unread limit=5
hal-comms call mail_search query="interview" days=14
hal-comms call mail_summarise
```

### Configuration

Hal ships with no mail account. With none configured, every mail tool fails with
`no mail account configured: add [mail.accounts.<name>] to ~/.config/hal/config.toml`.
Accounts live in the `[mail]` table of that file; `default` may be left out when there is one:

```toml
[mail]
default = "personal"
[mail.accounts.personal]
address = "you@gmail.com"
imap = "imap.gmail.com"
smtp = "smtp.gmail.com"
password_file = "~/.config/hal/mail-personal"
```

## phone

hal-phone connects Hal to your phone through KDE Connect: ring it when it is lost, check its battery,
send it files, links and text, read its notifications, and send a text message from it.

### Highlights

- "Hal, where's my phone?" rings it at full volume.
- Files, links and text sent from the computer to the phone.
- The phone's notifications and battery level.
- SMS from the phone's own number; Hal asks before sending.

### Use

Run a tool with `hal-comms call phone_<tool>`:

```bash
hal-comms call phone_ring
hal-comms call phone_send_file path=~/Documents/ticket.pdf
```

### Configuration

Settings live in the `[phone]` table of `~/.config/hal/config.toml`:

```toml
[phone]
phone = "Pixel"      # which paired device to use when there are several
```

## telegram

hal-telegram lets you talk to Hal from your phone through a Telegram bot. Messages and voice notes
are answered by Hal through `hal acp --channel telegram --toolset assistant`, so every turn runs in the
box, and a few commands
cover the job search and the daily briefing.

### Highlights

- Free text is an ACP prompt to `hal acp`: "add the dentist on thursday at ten" lands in the
  calendar, as it would by voice. The bridge keeps no brain of its own.
- One conversation per chat until `/reset`. A turn that runs past `turn_timeout_s` is cancelled.
- A tool call that needs approval arrives as a message with the exact arguments and Allow once and
  Deny buttons. Only a press from the paired chat counts. A request longer than 3500 characters
  has only Deny and the line "Approve with: hal approve <id>".
- Link previews are off on every message.
- Voice notes go through the `hal-voice` CLI (`transcribe-file`, `tts`). Without it the bot says
  "voice notes need hal-voice".
- Job commands go through hal-jobs, and `/brief` through hal-briefing, by way of hal-hub.
- A pairing code is valid for 10 minutes. Five wrong codes in 10 minutes lock pairing until the
  bridge restarts, and a desktop notification says so.
- Answers one paired chat only; anyone else who finds the bot is ignored.

### Set up the bot

1. In Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot` and follow the prompts.
   It replies with a token like `123456789:AA...`.
2. Save the token (it goes in `~/.config/hal/telegram-token`, readable only by you):

   ```bash
   cd ~/src/hal-ecosystem/extensions/hal-telegram
   python3 -m haltelegram token 123456789:AA...
   ```

3. Start the service. A desktop notification shows a pairing code; send `/pair <code>` to your bot.
   The chat is saved in `~/.config/hal/telegram-chat`, which hal-notify also uses for alerts.

`python3 -m haltelegram status` shows whether a token is saved and a chat paired, and
`python3 -m haltelegram unpair` forgets the chat so the next start shows a new code.

### Use

Anything that is not a command is a message for Hal. The commands are:

| Command | Does |
| --- | --- |
| `/status` | What needs you, and the pipeline |
| `/queue` | Jobs ready to apply for |
| `/todo`, `/todo <text>` | The job to-do list, or add to it |
| `/discard <id>`, `/shortlist <id>`, `/applied <id>` | Record a job's progress |
| `/jobs` | Best unreviewed matches, with ids |
| `/pack <id>` | Draft an application pack and send its files |
| `/brief` | Today's briefing, as text and a voice note |
| `/reset` | Start a new conversation |

Each job command calls one hal-jobs tool through hal-hub: `/status` is `jobs_status`, `/jobs` is
`jobs_matches`, `/queue` is `jobs_queue`, `/todo` is `jobs_todo` or `jobs_todo_add`, `/shortlist` is
`jobs_shortlist`, `/discard` and `/applied` are `jobs_mark`, and `/pack` is `jobs_pack`. Without
hal-jobs they say so.

### Configuration

Settings live in the `[telegram]` table of `~/.config/hal/config.toml`:

```toml
[telegram]
voice_replies = true         # answer voice notes and /brief with a voice note
turn_timeout_s = 600         # seconds a chat turn may take before it is cancelled
```

The job commands find jobhunt through hal-jobs' own `[jobs]` settings.
