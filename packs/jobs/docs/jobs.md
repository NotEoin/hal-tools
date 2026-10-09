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

## Install

hal-jobs needs Python 3.11 or later and a jobhunt checkout (the employment-helper repository).

```bash
git clone <url> ~/src/hal-ecosystem/hal-jobs
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub jobs_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-jobs
python3 -m haljobs queue
python3 -m haljobs digest
python3 -m haljobs mark job=acme status=interview
```

## Configuration

Settings live in the `[jobs]` table of `~/.config/hal/config.toml`:

```toml
[jobs]
jobhunt = "~/src/employment-helper"
employment_url = "http://127.0.0.1:8737/"
```

## Licence

MIT. See [LICENSE](LICENSE).
