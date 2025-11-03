import os
import re
import asyncio
import sys
import logging
import shutil
from typing import Dict, Tuple, List

import discord
from discord import app_commands
from discord.ext import commands

# -------------------------
# Config
# -------------------------
AI_NAME = "NightshadeAI"
MAX_QUESTIONS_PER_SERVER = 400
AI_TIMEOUT_SEC = 240                 # overall PS roundtrip timeout
PER_USER_COOLDOWN_SEC = 4            # simple flood control
THINKING_MESSAGE = "⏳ Thinking…"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POWERSHELL_SCRIPT = os.path.join(SCRIPT_DIR, "BackgroundAI_Bot.ps1")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ DISCORD_TOKEN env var not set.", file=sys.stderr)
    sys.exit(1)

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("nightshade-bot")

# -------------------------
# Intents / Bot
# -------------------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
server_question_count: Dict[int, int] = {}
guild_locks: Dict[int, asyncio.Lock] = {}
last_user_ask_at: Dict[Tuple[int, int], float] = {}  # (guild_id, user_id) -> ts

# -------------------------
# Utils
# -------------------------
BRAILLE_RE = re.compile(r'[\u2800-\u28FF]')
ANSI_RE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
PERSONA_TAG_RE = re.compile(r'(?im)^\s*NightshadeAI:\s*')

def clean_ai_output(text: str, remove_persona_tag: bool = True) -> str:
    if not text:
        return ""
    text = BRAILLE_RE.sub('', text)
    text = ANSI_RE.sub('', text)
    if remove_persona_tag:
        text = PERSONA_TAG_RE.sub('', text)
    text = re.sub(r'(\r?\n){3,}', '\n\n', text)
    return text.strip()

def split_discord_message(text: str, limit: int = 2000) -> List[str]:
    chunks = []
    while len(text) > limit:
        split_pos = text.rfind('\n', 0, limit)
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, limit)
        if split_pos == -1:
            split_pos = limit
        chunks.append(text[:split_pos].strip())
        text = text[split_pos:].strip()
    if text:
        chunks.append(text)
    return chunks

def powershell_prefix() -> List[str]:
    # Prefer pwsh (Core) if present; fallback to Windows PowerShell
    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            return [exe, "-NoProfile", "-ExecutionPolicy", "Bypass"]
    raise FileNotFoundError("PowerShell executable not found")

def mentions_none() -> discord.AllowedMentions:
    return discord.AllowedMentions.none()

async def ask_ai_async(question: str) -> Tuple[str, int]:
    if not os.path.isfile(POWERSHELL_SCRIPT):
        return ("⚠️ AI backend script is missing.", 1)

    args = powershell_prefix() + ["-File", POWERSHELL_SCRIPT, "-Prompt", question]

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=AI_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            proc.kill()
            return (f"⚠️ AI timed out after {AI_TIMEOUT_SEC}s. Try again with a shorter question.", 124)

        exit_code = await proc.wait()
        raw = (stdout or b"").decode("utf-8", errors="ignore")
        cleaned = clean_ai_output(raw)
        if not cleaned:
            cleaned = "⚠️ AI returned no response."
        return (cleaned, exit_code)

    except FileNotFoundError:
        return ("❌ PowerShell (pwsh/powershell) not found. Install PowerShell 7 or fix PATH.", 127)
    except Exception as e:
        log.exception("Error calling AI")
        return (f"⚠️ Error calling AI: {e}", 1)

def is_cooldown_ok(guild_id: int, user_id: int, now: float) -> bool:
    key = (guild_id, user_id)
    last = last_user_ask_at.get(key, 0.0)
    if now - last >= PER_USER_COOLDOWN_SEC:
        last_user_ask_at[key] = now
        return True
    return False

# -------------------------
# Slash commands
# -------------------------
@bot.event
async def on_ready():
    log.info("%s is online!", AI_NAME)
    try:
        await bot.tree.sync()
        log.info("Application commands synced.")
    except Exception as e:
        log.exception("Slash sync error: %s", e)

@bot.tree.command(name="start", description="Create an #ai channel for chatting with the bot")
async def start(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("❌ This command only works in a server.", ephemeral=True)
        return

    existing = discord.utils.get(guild.text_channels, name="ai")
    if existing:
        await interaction.response.send_message("⚠️ #ai channel already exists.", ephemeral=True)
        return

    try:
        channel = await guild.create_text_channel("ai")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don’t have permission to create channels.", ephemeral=True)
        return

    server_question_count[guild.id] = 0
    guild_locks[guild.id] = asyncio.Lock()
    await interaction.response.send_message(f"✅ AI channel created: {channel.mention}", ephemeral=True)

@bot.tree.command(name="aiinfo", description="Show NightshadeAI status for this server")
async def aiinfo(interaction: discord.Interaction):
    gid = interaction.guild_id
    cnt = server_question_count.get(gid, 0)
    await interaction.response.send_message(
        f"**{AI_NAME} server status**\nQuestions used: **{cnt} / {MAX_QUESTIONS_PER_SERVER}**\nTimeout: **{AI_TIMEOUT_SEC}s**\nPer-user cooldown: **{PER_USER_COOLDOWN_SEC}s**",
        ephemeral=True
    )

@bot.tree.command(name="resetcounter", description="(Admin) Reset the NightshadeAI question counter for this server")
@app_commands.checks.has_permissions(manage_guild=True)
async def resetcounter(interaction: discord.Interaction):
    gid = interaction.guild_id
    server_question_count[gid] = 0
    await interaction.response.send_message("✅ Counter reset.", ephemeral=True)

@resetcounter.error
async def resetcounter_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Manage Server** to use this.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Error processing command.", ephemeral=True)

# -------------------------
# Respond in #ai channel on mention
# -------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    await bot.process_commands(message)

    ai_channel = discord.utils.get(message.guild.text_channels, name="ai")
    if ai_channel is None or message.channel.id != ai_channel.id:
        return

    if not bot.user or not bot.user.mentioned_in(message):
        return

    guild_id = message.guild.id
    user_id = message.author.id
    server_question_count.setdefault(guild_id, 0)
    guild_locks.setdefault(guild_id, asyncio.Lock())

    if server_question_count[guild_id] >= MAX_QUESTIONS_PER_SERVER:
        await message.channel.send(
            f"❌ {AI_NAME} has reached the question limit for this server.",
            allowed_mentions=mentions_none()
        )
        return

    now = asyncio.get_event_loop().time()
    if not is_cooldown_ok(guild_id, user_id, now):
        await message.channel.send(
            f"⚠️ Slow down a bit—try again in ~{PER_USER_COOLDOWN_SEC}s.",
            allowed_mentions=mentions_none()
        )
        return

    # Strip bot mentions to get the user's question
    user_question = message.content
    for mention in message.mentions:
        user_question = user_question.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
    user_question = user_question.strip()
    if not user_question:
        await message.channel.send(
            "⚠️ Please ask a question after mentioning me.",
            allowed_mentions=mentions_none()
        )
        return

    server_question_count[guild_id] += 1

    async with guild_locks[guild_id]:
        thinking_msg = await message.channel.send(THINKING_MESSAGE, allowed_mentions=mentions_none())
        response, exit_code = await ask_ai_async(user_question)
        try:
            await thinking_msg.delete()
        except discord.HTTPException:
            pass

        # Tag nonzero exit with a subtle prefix to aid debugging
        prefix = "" if exit_code == 0 else f"[exit {exit_code}] "
        for chunk in split_discord_message(prefix + response):
            await message.channel.send(
                f"🤖 {AI_NAME}:\n{chunk}",
                allowed_mentions=mentions_none()
            )

# -------------------------
# Run bot
# -------------------------
bot.run(TOKEN)
