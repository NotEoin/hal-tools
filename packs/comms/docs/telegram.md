# hal-telegram

hal-telegram lets you talk to Hal from your phone through a Telegram bot. Messages and voice notes
are answered by core Hal's brain with the tools of every installed extension, and a few commands
cover the job search and the daily briefing.

## Highlights

- Free text is answered by Hal's local brain, which can use any installed tool: "add the dentist on
  thursday at ten" lands in the calendar, as it would by voice.
- One conversation per chat, kept in memory until `/reset`; long jobs run in the background and the
  result is sent when they finish.
- Voice notes are transcribed locally with faster-whisper, and answered with a voice note in HAL's
  voice when hal-voice's server is running.
- Job commands go through hal-jobs, and `/brief` through hal-briefing, by way of hal-hub.
- Answers one paired chat only; anyone else who finds the bot is ignored.

## Install

hal-telegram needs Python 3.11 or later and core Hal; voice notes need hal-voice. It lives in
`extensions/hal-telegram` and is installed by the ecosystem installer, which renders
`systemd/hal-telegram.service` (`@ROOT@`, `@CORE@`, `@ECOSYSTEM@`) into `~/.config/systemd/user`:

```bash
hal ext add telegram
```

The service runs under hal-voice's virtualenv when it is there, for faster-whisper, and under
`python3` (text only) when it is not. It belongs to `hal.target` and is marked `X-HalGPU=yes`, since
it runs the local model, so `hal off` stops it.

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

`/queue`, `/todo`, `/discard` and `/applied` use hal-jobs' tools. `/status`, `/jobs`, `/shortlist`,
`/pack` and adding a to-do have no hal-jobs tool yet, so they run jobhunt directly.

## Configuration

Settings live in the `[telegram]` table of `~/.config/hal/config.toml`; the brain itself follows
`[brain]`:

```toml
[telegram]
persona = ""                 # empty = [brain].persona, else core Hal's own
model = ""                   # empty = [brain].model, else [hal].chat_model
whisper_model = "small.en"   # for voice notes
whisper_device = "cpu"       # cpu | cuda | auto
voice_replies = true         # answer voice notes and /brief with a voice note

[jobs]
jobhunt_root = "~/src/employment-helper"
```

## Licence

MIT. See [LICENSE](LICENSE).
