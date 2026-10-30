# work

The `work` pack: files, development and language tools. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-work   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## dev

hal-dev tells Hal about your code: every git repository's branch, uncommitted work and unpushed
commits, recent history and changes, TODO comments, whether the tests pass, and your GitHub pull
requests and issues.

### Highlights

- Finds every repository under the configured folders, skipping virtual environments and vendored code.
- Uncommitted files, commits ahead or behind the upstream, and the last commit, in one call.
- TODO, FIXME, HACK and XXX comments in tracked files.
- Runs a project's tests with npm, cargo, pytest or unittest, whichever it uses.
- GitHub pull requests, issues and notifications through the `gh` command.
- Reads only: it never commits, pushes or switches branches.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub dev_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-dev
python3 -m haldev repos dirty_only=true
python3 -m haldev run_tests repo=hal-hub
python3 -m haldev todos repo=hatch
```

### Configuration

Settings live in the `[dev]` table of `~/.config/hal/config.toml`:

```toml
[dev]
roots = ["~/src", "~/projects"]   # where repositories are looked for; missing ones are skipped
depth = 2                         # how many folders deep
```

## files

hal-files lets Hal find, read and tidy your files: search by name, kind, size or age, list what
changed recently, read or summarise documents including PDFs and Word files, find what fills the
disk, spot duplicates, and sort the Downloads folder.

### Highlights

- Searches skip caches, virtual environments, `.git`, `node_modules` and the trash, so results are your files.
- Kinds: documents, spreadsheets, presentations, images, videos, audio, archives, code and installers.
- Reads text, Markdown, code, PDF (through `pdftotext`), Word, OpenDocument and PowerPoint, and
  summarises with the local model.
- Largest folders and files, duplicates by content hash, and the size of any folder.
- Tidying Downloads moves files into folders by kind and never overwrites; it asks first.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub files_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-files
python3 -m halfiles find name=invoice kind=documents modified_days=30
python3 -m halfiles read path=~/Downloads/contract.pdf summarise=true
python3 -m halfiles largest folder=~
```

### Configuration

Settings live in the `[files]` table of `~/.config/hal/config.toml`:

```toml
[files]
roots = ["~/Documents", "~/Downloads", "~/Desktop", "~/Pictures"]   # searched when no folder is named
```

## lang

hal-lang does language work with the local model: translation, proofreading, rewriting in a tone,
summaries, plain-English explanations and draft replies. Give it text, or copy text and ask Hal.

### Highlights

- Every tool works on the text given, or on the clipboard when none is.
- Proofreading fixes only spelling (British by default), grammar and punctuation, and lists each change.
- Rewrites keep every fact while changing tone and length.
- Explanations of letters, contract clauses, jargon or code, pitched at whoever is asking.
- Runs on the local model; nothing leaves the machine.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub lang_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-lang
python3 -m hallang translate text="Where is the station?" to=Japanese
python3 -m hallang rewrite tone=professional length=shorter
python3 -m hallang explain text="The lessee shall indemnify the lessor..."
```

### Configuration

Summaries and rewrites use the Hal gateway chat model (`hal-chat`); there is no per-pack model setting.
