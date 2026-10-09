# hal-files

hal-files lets Hal find, read and tidy your files: search by name, kind, size or age, list what
changed recently, read or summarise documents including PDFs and Word files, find what fills the
disk, spot duplicates, and sort the Downloads folder.

## Highlights

- Searches skip caches, virtual environments, `.git`, `node_modules` and the trash, so results are your files.
- Kinds: documents, spreadsheets, presentations, images, videos, audio, archives, code and installers.
- Reads text, Markdown, code, PDF (through `pdftotext`), Word, OpenDocument and PowerPoint, and
  summarises with the local model.
- Largest folders and files, duplicates by content hash, and the size of any folder.
- Tidying Downloads moves files into folders by kind and never overwrites; it asks first.

## Install

hal-files needs Python 3.11 or later; `pdftotext` (poppler-utils) for PDFs and Ollama for summaries.

```bash
git clone <url> ~/src/hal-ecosystem/hal-files
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub files_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-files
python3 -m halfiles find name=invoice kind=documents modified_days=30
python3 -m halfiles read path=~/Downloads/contract.pdf summarise=true
python3 -m halfiles largest folder=~
```

## Configuration

Settings live in the `[files]` table of `~/.config/hal/config.toml`:

```toml
[files]
roots = ["~/Documents", "~/Downloads", "~/Desktop", "~/Pictures"]   # searched when no folder is named
```

## Licence

MIT. See [LICENSE](LICENSE).
