# hal-telegram

hal-telegram lets you talk to Hal from your phone through a Telegram bot. Messages and voice notes
are answered by Hal through `hal acp --channel telegram --toolset assistant`, so every turn runs in the
box, and a few commands
cover the job search and the daily briefing.

## Highlights

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

## Install

hal-telegram needs Python 3.11 or later and Hal; voice notes need hal-voice. The manifest lists
`systemd/hal-telegram.service`, which the installer renders (`@ROOT@`, `@PYTHON@`) into
`~/.config/systemd/user`:

```bash
hal ext add telegram
```

The bridge needs `hal` and, for voice notes, `hal-voice` on `PATH`. If `hal acp` is missing or
exits, the bot answers "Hal is not available" and starts it again on the next message.

## Set up the bot

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

## Use

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

## Configuration

Settings live in the `[telegram]` table of `~/.config/hal/config.toml`:

```toml
[telegram]
voice_replies = true         # answer voice notes and /brief with a voice note
turn_timeout_s = 600         # seconds a chat turn may take before it is cancelled
```

The job commands find jobhunt through hal-jobs' own `[jobs]` settings.

## Licence

MIT. See [LICENSE](LICENSE).
