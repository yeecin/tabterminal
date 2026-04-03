# tabterminal

**TabTerminal** is a cross-platform terminal shell (Windows & Linux) with:

- **Tab completion** – system executables, file paths, and previously typed commands
- **Inline history suggestions** – fish-shell-style suggestions as you type (accept with <kbd>→</kbd> or <kbd>End</kbd>)
- **AI-powered predictions** – uses any OpenAI-compatible API to predict the next command based on your recent history

---

## Requirements

- Python ≥ 3.8
- Works on **Linux**, **macOS**, and **Windows**

## Installation

```bash
pip install tabterminal
```

Or from source:

```bash
git clone https://github.com/yeecin/tabterminal.git
cd tabterminal
pip install -e .
```

## Quick start

```bash
tabterminal
```

You will see a prompt showing your current directory:

```
~/projects ❯ _
```

Type any shell command and press <kbd>Enter</kbd> to execute it.  
Press <kbd>Tab</kbd> to see completions; use <kbd>→</kbd> to accept an inline suggestion.

## Enabling AI predictions

TabTerminal calls an OpenAI-compatible chat API to predict commands.  
Set your API key once and it is stored in `~/.tabterminal/config.json`:

```
~/projects ❯ ai key sk-your-openai-api-key
  API key saved.
```

Or export the environment variable before launching:

```bash
export OPENAI_API_KEY=sk-your-openai-api-key
tabterminal
```

After every command execution, TabTerminal asynchronously fetches a prediction
and displays it as a *💡 AI suggests:* hint at the start of the next prompt.

### Using a custom / self-hosted model

```
❯ ai url https://your-api-endpoint/v1
❯ ai model your-model-name
```

## Built-in commands

| Command | Description |
|---|---|
| `help` | Show usage information |
| `cd [dir]` | Change working directory |
| `exit` / `quit` | Exit TabTerminal |
| `ai status` | Show AI configuration |
| `ai key <key>` | Set OpenAI API key |
| `ai model <name>` | Set model (e.g. `gpt-4`) |
| `ai url <url>` | Set API base URL |
| `ai enable` / `ai disable` | Toggle AI predictions |
| `config list` | Show all settings |
| `config get <key>` | Show one setting |
| `config set <key> <val>` | Change a setting |

## Keyboard shortcuts

| Key | Action |
|---|---|
| <kbd>Tab</kbd> | Trigger completion menu |
| <kbd>→</kbd> / <kbd>End</kbd> | Accept inline history suggestion |
| <kbd>↑</kbd> / <kbd>↓</kbd> | Navigate command history |
| <kbd>Ctrl+R</kbd> | Reverse-search history |
| <kbd>Ctrl+C</kbd> | Cancel current line |
| <kbd>Ctrl+D</kbd> | Exit shell |

## Configuration

Settings are stored in `~/.tabterminal/config.json`.

| Key | Default | Description |
|---|---|---|
| `api_key` | `""` | OpenAI API key |
| `api_base_url` | `https://api.openai.com/v1` | API endpoint |
| `model` | `gpt-3.5-turbo` | Chat model |
| `ai_enabled` | `true` | Enable/disable AI |
| `max_history_size` | `10000` | Max history entries |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
