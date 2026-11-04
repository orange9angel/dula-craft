# 配置说明

大部分情况不需要配置。下面的内容都是可选的。

## 检查环境

在 AI 工具里说“检查 dula-craft 环境”，或者自己运行：

```bash
python ~/.dula-craft/repo/skills/dula-start/scripts/doctor.py --fix
```

Windows 的路径是 `%USERPROFILE%\.dula-craft\repo\skills\dula-start\scripts\doctor.py`。

`--fix` 只会在 `~/.dula-craft` 里建环境，不改动系统。

## 必需的软件

| 软件 | 检查命令 | Windows | macOS | Ubuntu/Debian |
|---|---|---|---|---|
| git | `git --version` | `winget install Git.Git` | `xcode-select --install` | `sudo apt install git` |
| Python 3.9+ | `python --version` | `winget install Python.Python.3.12` | `brew install python` | `sudo apt install python3 python3-venv` |
| ffmpeg | `ffmpeg -version` | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |

装完请重新打开终端。

## 出图

| 方式 | 怎么配置 |
|---|---|
| **Codex CLI（全自动）** | 安装并登录 [Codex CLI](https://github.com/openai/codex)，就会自动使用。消耗你的 ChatGPT 订阅额度 |
| **手动** | 不用配置。工具会把提示词和保存路径写进 `build/images_todo.md`，你用任何出图工具画好放回去，再重跑一次 |

请确认你用的出图工具允许你这样使用生成的图片。

## 配音

| 方式 | 怎么配置 |
|---|---|
| **自己的音频** | 不用配置。把 mp3、wav 放到 `audio/voice/<台词id>.wav` |
| **火山 Seed-Audio** | 按下面三步 |
| **先不配音** | 不用配置。在台词上写 `seconds` 占位，做无声样片 |

配置火山 Seed-Audio：

1. [开通“音频生成 1.0”](https://console.volcengine.com/speech/new/setting/activate)。
2. [创建 API Key](https://console.volcengine.com/speech/new/setting/apikeys)。要在语音控制台创建，和方舟的 Key 不通用。
3. 在你自己的终端运行，把 Key 粘贴进去。屏幕不会显示你的输入：

   ```bash
   python ~/.dula-craft/repo/skills/dula-start/scripts/configure.py
   ```

其他操作：

```bash
python .../configure.py --status   # 只显示是否已设置，不显示内容
python .../configure.py --remove   # 删除
```

**保护好密钥：** 不要把它发给 AI，也不要写进影片目录。密钥存在 `~/.dula-craft/config.env`，不在任何
项目目录里。如果不小心泄露了，去火山控制台作废，再换一把新的。

也可以改用环境变量 `VOLC_SPEECH_API_KEY`，它优先于配置文件。

## 音乐

把你有权使用的音乐放进 `audio/music/`，告诉 AI 用哪一首。工具不生成音乐，对白时会自动压低音乐音量。

## 安装位置

| 位置 | 内容 |
|---|---|
| `~/.dula-craft/repo` | 程序本体 |
| `~/.dula-craft/venv` | Python 环境 |
| `~/.dula-craft/config.env` | 你的密钥（如果配置了） |
| `~/.claude/skills/dula-*` | 给 Claude Code 的链接 |
| `~/.agents/skills/dula-*` | 给 Codex、Kimi Code 的链接 |

想换位置，安装前设置环境变量 `DULA_CRAFT_HOME`。

已有同名内容时，安装程序会跳过并提示，不会覆盖。

## 更新

重新运行安装命令。

## 卸载

只删除它自己装的东西，包括保存的密钥。你的影片目录不受影响。

Windows（PowerShell）：

```powershell
$env:DULA_CRAFT_UNINSTALL='1'; irm https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.ps1 | iex; Remove-Item Env:DULA_CRAFT_UNINSTALL
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.sh | bash -s -- --uninstall
```

## 通过 Claude Code 插件安装

只用 Claude Code 时可以走插件，不需要运行上面的安装脚本（两种方式选一种）：

```text
/plugin marketplace add orange9angel/dula-craft
/plugin install dula-craft@dula-craft
```

卸载：`/plugin marketplace remove dula-craft`。
