# hal-jobs

hal-jobs connects Hal to the job search: the application queue, applications by stage, the job
to-do list, the job inbox and a spoken summary, through jobhunt's command line and the Hal
Employment web app.

## Highlights

- Holds no job data: it calls jobhunt and Hal Employment, so they stay the single source of truth.
- The queue and applications from Hal Employment's API, with jobhunt as the fallback.
- Checks the job inbox on request and reads out what needs attention.
- Records progress (applied, interview, offer, rejected) by job id or name.
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

## Configuration

Settings live in the `[jobs]` table of `~/.config/hal/config.toml`:

```toml
[jobs]
jobhunt_root = "~/src/employment-helper"
employment_url = "http://127.0.0.1:8737/"
```

The older key `jobhunt` is still read when `jobhunt_root` is not set.

## Licence

MIT. See [LICENSE](LICENSE).
