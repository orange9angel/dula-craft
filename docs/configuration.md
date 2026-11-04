# Configuration

Most people don't need to configure anything. Everything below is optional.

## Check your setup

Tell your agent "check my dula-craft setup", or run this yourself:

```bash
python ~/.dula-craft/repo/skills/dula-start/scripts/doctor.py --fix
```

On Windows, the path is `%USERPROFILE%\.dula-craft\repo\skills\dula-start\scripts\doctor.py`.

`--fix` only creates an environment inside `~/.dula-craft`. It doesn't change your system.

## Required software

| Software | Check | Windows | macOS | Ubuntu/Debian |
|---|---|---|---|---|
| git | `git --version` | `winget install Git.Git` | `xcode-select --install` | `sudo apt install git` |
| Python 3.9+ | `python --version` | `winget install Python.Python.3.12` | `brew install python` | `sudo apt install python3 python3-venv` |
| ffmpeg | `ffmpeg -version` | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |

Open a new terminal after installing.

## Images

| Option | Setup |
|---|---|
| **Codex CLI (automatic)** | Install and sign in to [Codex CLI](https://github.com/openai/codex). It's used automatically and draws on your ChatGPT plan |
| **By hand** | No setup. The prompts and save paths are written to `build/images_todo.md`. Make the images with any tool, save them, and run the command again |

Check that your image tool's terms allow your intended use.

## Voices

| Option | Setup |
|---|---|
| **Your own audio** | No setup. Put mp3 or wav files at `audio/voice/<line id>.wav` |
| **Volcano Engine Seed-Audio** | Follow the steps below |
| **No voices yet** | No setup. Give each line a `seconds` value to make a silent draft |

To set up Seed-Audio:

1. [Enable "Audio Generation 1.0"](https://console.volcengine.com/speech/new/setting/activate).
2. [Create an API key](https://console.volcengine.com/speech/new/setting/apikeys) in the speech console. Keys from the Ark console don't work.
3. In your own terminal, run this and paste the key. Your typing stays hidden.

   ```bash
   python ~/.dula-craft/repo/skills/dula-start/scripts/configure.py
   ```

To check or remove the key:

```bash
python .../configure.py --status   # Says whether a key is set, never what it is
python .../configure.py --remove   # Deletes it
```

**Keep your key safe.** Don't send it to your agent or put it in a film folder. It's stored in `~/.dula-craft/config.env`, outside every project. If it leaks, revoke it in the console and create a new one.

You can use the `VOLC_SPEECH_API_KEY` environment variable instead. It takes priority over the saved key.

## Music

Put music you have the rights to in `audio/music/` and tell your agent which track to use. This project doesn't generate music. Music is lowered automatically during dialogue.

## Where things are installed

| Location | Contents |
|---|---|
| `~/.dula-craft/repo` | The program |
| `~/.dula-craft/venv` | The Python environment |
| `~/.dula-craft/config.env` | Your key, if you set one |
| `~/.claude/skills/dula-*` | Links for Claude Code |
| `~/.agents/skills/dula-*` | Links for Codex and Kimi Code |

To use another location, set `DULA_CRAFT_HOME` before installing.

If something with the same name already exists, the installer skips it and tells you. It never overwrites anything.

## Update

Run the install command again.

## Uninstall

This removes only what the installer added, including your saved key. Your film folders are not touched.

Windows (PowerShell):

```powershell
$env:DULA_CRAFT_UNINSTALL='1'; irm https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.ps1 | iex; Remove-Item Env:DULA_CRAFT_UNINSTALL
```

macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.sh | bash -s -- --uninstall
```

## Install as a Claude Code plugin

If you only use Claude Code, you can use the plugin instead of the install script. Choose one or the other.

```text
/plugin marketplace add orange9angel/dula-craft
/plugin install dula-craft@dula-craft
```

To remove it: `/plugin marketplace remove dula-craft`.
