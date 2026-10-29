# hal-models

hal-models tells Hal about the local AI models: which are installed in Ollama, which are loaded and
how much GPU memory they take, and every program on the GPU. Hal can load, unload, download and
delete models, or ask a particular one a question.

## Highlights

- Installed models with size, family, parameters and quantisation.
- Loaded models with VRAM use and when they unload.
- The GPU's memory, use and temperature, with each program's command line.
- Unload everything to free the GPU before a game or a training run.
- Deleting a model asks for confirmation.

## Install

hal-models needs Python 3.11 or later and Ollama; GPU readings need `nvidia-smi`.

```bash
git clone <url> ~/src/hal-ecosystem/hal-models
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub models_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-models
python3 -m halmodels loaded
python3 -m halmodels unload
python3 -m halmodels ask model=qwen3.5:9b prompt="Name three moons of Jupiter."
```

## Configuration

The Ollama address is `ollama_url` in the `[hal]` table of `~/.config/hal/config.toml`.

## Licence

MIT. See [LICENSE](LICENSE).
