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

```bash
# clone repo
git clone https://github.com/dellpatcher/BackgroundAI-bot-discord-public.git
cd BackgroundAI-bot-discord-public/BackgroundAI-bot-discord-main/ai

# install requirements
pip install -r requirements.txt

# set your bot token
setx DISCORD_TOKEN "your_discord_bot_token_here"

# (optional) set Ollama host
setx OLLAMA_HOST "http://localhost:11434"

# run the bot
python bot.py
