# hal-lang

hal-lang does language work with the local model: translation, proofreading, rewriting in a tone,
summaries, plain-English explanations and draft replies. Give it text, or copy text and ask Hal.

## Highlights

- Every tool works on the text given, or on the clipboard when none is.
- Proofreading fixes only spelling (British by default), grammar and punctuation, and lists each change.
- Rewrites keep every fact while changing tone and length.
- Explanations of letters, contract clauses, jargon or code, pitched at whoever is asking.
- Runs on the local model; nothing leaves the machine.

## Install

hal-lang needs Python 3.11 or later and Ollama with a chat model.

```bash
git clone <url> ~/src/hal-ecosystem/hal-lang
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub lang_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-lang
python3 -m hallang translate text="Where is the station?" to=Japanese
python3 -m hallang rewrite tone=professional length=shorter
python3 -m hallang explain text="The lessee shall indemnify the lessor..."
```

## Configuration

The model is `chat_model` in the `[hal]` table of `~/.config/hal/config.toml`.

## Licence

MIT. See [LICENSE](LICENSE).
