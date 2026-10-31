# jobs

The `jobs` pack: an adapter to the Hal Employment job-search app. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-jobs   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## jobs

hal-jobs connects Hal to the job search: new matches, the application queue, applications by
stage, the job to-do list, the job inbox, application packs and written or spoken summaries,
through jobhunt's command line and the Hal Employment web app.

### Highlights

- Holds no job data: it calls jobhunt and Hal Employment, so they stay the single source of truth.
- The queue and applications from Hal Employment's API, with jobhunt as the fallback.
- Checks the job inbox on request and reads out what needs attention.
- Lists the best unreviewed matches with their ids, and records progress (shortlisted, applied,
  interview, offer, rejected) by job id or name.
- Adds to the job to-do list, and drafts a job's application pack on request.
- Opens Hal Employment, where every application is still submitted by its owner.
- Runs Hal Employment as a service, with a desktop launcher that starts it on demand.

### Use

Run a tool with `hal-jobs call jobs_<tool>`:

```bash
hal-jobs call jobs_queue
hal-jobs call jobs_digest
hal-jobs call jobs_mark job=acme status=interview
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

### Configuration

Settings live in the `[jobs]` table of `~/.config/hal/config.toml`:

```toml
[jobs]
jobhunt_root = "~/src/jobhunt"   # where you cloned jobhunt; required
employment_url = "http://127.0.0.1:8737/"
```

`jobhunt_root` has no default: the jobs tools fail with a config error until it is set. The older
key `jobhunt` is still read when `jobhunt_root` is not set.
