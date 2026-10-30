# hal-jobs

hal-jobs connects Hal to the job search: new matches, the application queue, applications by
stage, the job to-do list, the job inbox, application packs and written or spoken summaries,
through jobhunt's command line and the Hal Employment web app.

## Highlights

- Holds no job data: it calls jobhunt and Hal Employment, so they stay the single source of truth.
- The queue and applications from Hal Employment's API, with jobhunt as the fallback.
- Checks the job inbox on request and reads out what needs attention.
- Lists the best unreviewed matches with their ids, and records progress (shortlisted, applied,
  interview, offer, rejected) by job id or name.
- Adds to the job to-do list, and drafts a job's application pack on request.
- Opens Hal Employment, where every application is still submitted by its owner.
- Runs Hal Employment as a service, with a desktop launcher that starts it on demand.

## Install

hal-jobs needs Python 3.11 or later and a jobhunt checkout (the employment-helper repository). It
lives in `extensions/hal-jobs` and is installed by the ecosystem installer:

```bash
hal ext add jobs
```

The installer renders `systemd/hal-employment.service` and `desktop/hal-employment.desktop`,
replacing `@ROOT@` with this folder. The service runs `bin/hal-employment-serve`, which starts
`jobhunt serve` (Hal Employment, on http://127.0.0.1:8737) in `[jobs].jobhunt_root` with that
checkout's virtualenv. Its worker screens jobs and drafts packs with the local model, so the unit
is marked `X-HalGPU=yes` and `hal off` stops it. `bin/hal-employment`, which the desktop launcher
runs, starts the service if needed and opens the app in the browser.

## Use

The tools run from the module folder, or through hal-hub as `hal-hub jobs_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-jobs
python3 -m haljobs queue
python3 -m haljobs digest
python3 -m haljobs mark job=acme status=interview
```

| Tool | Does | jobhunt |
| --- | --- | --- |
| `jobs_queue` | Jobs ready to apply for, best first | Hal Employment API, else `queue` |
| `jobs_applications` | Applications by stage | Hal Employment API, else `list -s all` |
| `jobs_matches` | Best unreviewed matches, with ids | `list -m 60 -n 8` |
| `jobs_status` | The written status digest (not emailed) | `digest --dry-run` |
| `jobs_digest` | A short spoken summary | `digest --spoken` |
| `jobs_stats` | Counts by status and source | `stats` |
| `jobs_todo`, `jobs_todo_add` | The to-do list, or add to it | `todo`, `todo add` |
| `jobs_mark`, `jobs_shortlist` | Record a job's progress | `set ID STATUS` |
| `jobs_pack` | Draft a job's application pack (up to 30 minutes) | `pack ID` |
| `jobs_check_email` | Sync the job inbox | `mail -q` |
| `jobs_open` | Open Hal Employment | |

## Configuration

Settings live in the `[jobs]` table of `~/.config/hal/config.toml`:

```toml
[jobs]
jobhunt_root = "~/src/employment-helper"
employment_url = "http://127.0.0.1:8737/"
```

The older key `jobhunt` is still read when `jobhunt_root` is not set. While the `[jobs]` table is
absent from the config, `jobhunt_root` falls back to the old default and a warning is logged once;
write the table to silence it.

## Licence

MIT. See [LICENSE](LICENSE).
