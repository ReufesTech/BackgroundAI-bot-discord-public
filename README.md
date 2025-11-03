# 🤖 BackgroundAI Bot  
**Version:** 0.2.0-alpha  
**Project:** NightshadeAI Framework  

---

## 🧩 Description
**BackgroundAI** is a multi-model Discord AI bot powered by **Ollama** and a **custom PowerShell orchestrator**.  
It merges reasoning and creativity from multiple LLMs into one unified, human-like voice called **NightshadeAI**.

---

## ⚙️ Architecture

### 1️⃣ Frontend — Python / Discord.py  
- Handles Discord slash commands, mentions, and formatting  
- Forwards prompts to the PowerShell backend  
- Async, non-blocking subprocess execution  
- Rate-limiting and per-guild cooldowns  

### 2️⃣ Middleware — PowerShell Orchestrator (`BackgroundAI_Bot.ps1`)  
- Runs **multiple Ollama models in parallel**  
- Cleans and merges model outputs  
- Auto-pulls missing models (optional)  
- Applies consistent NightshadeAI persona  

### 3️⃣ Backend — Summarizer AI  
- Merges drafts from all models  
- Produces a final, unified answer in a single consistent voice  

---

## 🧠 Active Models
| Role | Model | Description |
|------|--------|-------------|
| Reasoning / Analysis | **LLaMA2-Uncensored 7B** | Logical and factual responses |
| Creative Phrasing | **Mistral-OpenOrca 7B** | Natural and expressive wording |
| Final Composer | **Mistral-OpenOrca 7B** | Summarizes and refines output |

---

## ✨ Features
- 🧵 **Parallel model fan-out + summarization merge**
- ⚙️ **PowerShell backend orchestration** via Ollama
- 💬 `/start` command creates a dedicated `#ai` channel
- 📢 Responds automatically when mentioned inside `#ai`  
- 🧹 Cleans responses (removes spinners, ANSI codes, non-printables)  
- 📏 Splits messages safely to Discord’s 2000-char limit  
- 🧠 Persona override via `NIGHTSHADE_PERSONA` env variable  
- 🔒 Per-server question limits (default **400**)  
- 🕒 Per-user cooldowns to prevent flooding  
- 🔍 Structured logging for debugging  
- 🌐 Supports local or remote Ollama daemons (`OLLAMA_HOST`)

---

## 🛠️ Prerequisites

Make sure the following tooling is available before launching the bot:

- **PowerShell 7+** — required for the orchestrator script. Install via [PowerShell official docs](https://learn.microsoft.com/powershell/scripting/install/installing-powershell).
- **Ollama CLI** — used to host local language models. Follow the [Ollama installation guide](https://github.com/ollama/ollama#ollama).
- **Ollama models** — ensure the models listed below are available locally so they can be orchestrated:
  - `llama2-uncensored:7b`
  - `mistral-openorca:7b`

The Python layer invokes `BackgroundAI_Bot.ps1`, so `pwsh` (PowerShell 7) or `powershell` must be discoverable on your `PATH`. Runtime configuration relies on these environment variables:

- `DISCORD_TOKEN` — Discord bot token.
- `OLLAMA_HOST` — URL of the Ollama daemon (defaults to `http://localhost:11434`).
- `NIGHTSHADE_PERSONA` — override text for the default persona prompt.

Before starting `python ai/bot.py`, confirm your environment is ready:

```bash
pwsh --version
ollama list
```

If the required models are missing from `ollama list`, pull them first (e.g., `ollama pull llama2-uncensored:7b`).

---

## 🔧 Configuration

Customize the bot’s runtime behavior with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_NAME` | `NightshadeAI` | Display name used in responses and status messages. |
| `MAX_QUESTIONS_PER_SERVER` | `400` | Maximum number of questions allowed per guild before requiring a reset (must be a positive integer). |
| `AI_TIMEOUT_SEC` | `240` | Timeout, in seconds, for the PowerShell backend round trip (must be a positive number). |
| `PER_USER_COOLDOWN_SEC` | `4` | Minimum seconds users must wait between questions in the same guild (must be a positive number). |
| `THINKING_MESSAGE` | `⏳ Thinking…` | Message shown while the AI is generating a reply. |

All numeric values must be set to positive numbers; invalid values will prevent the bot from starting.

---

## ⚡ Quick Start

> ℹ️ The bot requires **Python 3.10+** and the [`discord.py`](https://pypi.org/project/discord.py/) package.

```bash
# clone repo
git clone https://github.com/dellpatcher/BackgroundAI-bot-discord-public.git
cd BackgroundAI-bot-discord-public/BackgroundAI-bot-discord-main/ai

# install dependencies
pip install --upgrade pip
pip install discord.py

# set your bot token
setx DISCORD_TOKEN "your_discord_bot_token_here"

# (optional) set Ollama host
setx OLLAMA_HOST "http://localhost:11434"

# run the bot
python bot.py
```
