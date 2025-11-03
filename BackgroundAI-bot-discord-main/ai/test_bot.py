import asyncio
import importlib
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


def _install_discord_stub():
    discord_stub = types.ModuleType("discord")

    class AllowedMentions:
        @staticmethod
        def none():
            return None

    class Intents:
        @staticmethod
        def default():
            intents = types.SimpleNamespace()
            intents.messages = False
            intents.message_content = False
            intents.guilds = False
            return intents

    discord_stub.AllowedMentions = AllowedMentions
    discord_stub.Intents = Intents
    discord_stub.HTTPException = Exception
    discord_stub.Forbidden = type("Forbidden", (Exception,), {})
    discord_stub.Interaction = type("Interaction", (), {})
    discord_stub.Message = type("Message", (), {})
    discord_stub.utils = types.SimpleNamespace(get=lambda *args, **kwargs: None)

    app_commands_stub = types.ModuleType("discord.app_commands")

    def _passthrough_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def _command_decorator(*args, **kwargs):
        def decorator(func):
            def error(handler):
                return handler

            func.error = error
            return func

        return decorator

    class Checks:
        @staticmethod
        def has_permissions(**kwargs):
            return _passthrough_decorator

    app_commands_stub.checks = Checks
    app_commands_stub.MissingPermissions = type("MissingPermissions", (Exception,), {})
    app_commands_stub.AppCommandError = Exception
    app_commands_stub.command = _command_decorator

    discord_stub.app_commands = app_commands_stub

    commands_stub = types.ModuleType("discord.ext.commands")

    class FakeBot:
        def __init__(self, *args, **kwargs):
            async def _async_noop(*_args, **_kwargs):
                return None

            self.tree = types.SimpleNamespace(
                sync=_async_noop,
                command=_command_decorator,
            )

        def event(self, func):
            return func

        async def process_commands(self, *_args, **_kwargs):
            return None

        def run(self, *_args, **_kwargs):
            return None

    commands_stub.Bot = FakeBot

    discord_ext_stub = types.ModuleType("discord.ext")
    discord_ext_stub.commands = commands_stub

    sys.modules.setdefault("discord", discord_stub)
    sys.modules.setdefault("discord.app_commands", app_commands_stub)
    sys.modules.setdefault("discord.ext", discord_ext_stub)
    sys.modules.setdefault("discord.ext.commands", commands_stub)


_install_discord_stub()

os.environ.setdefault("DISCORD_TOKEN", "test-token")

from ai import bot


class CleanAiOutputTests(unittest.TestCase):
    def test_strips_persona_and_noise_and_collapses_blank_lines(self):
        raw = (
            "NightshadeAI: Hello\x1b[31m World\x1b[0m\n"
            "  nightshadeai: Second\u2800line\n"
            "\n\n\n"
            "Third line\u2801\n"
            "\n\n\n"
        )

        cleaned = bot.clean_ai_output(raw)

        self.assertEqual("Hello World\nSecondline\n\nThird line", cleaned)

    def test_preserves_persona_prefix_when_requested(self):
        raw = "NightshadeAI: Reply with persona intact."

        cleaned = bot.clean_ai_output(raw, remove_persona_tag=False)

        self.assertEqual("NightshadeAI: Reply with persona intact.", cleaned)


class SplitDiscordMessageTests(unittest.TestCase):
    def test_returns_single_chunk_when_under_limit(self):
        text = "short message"

        chunks = bot.split_discord_message(text, limit=50)

        self.assertEqual(["short message"], chunks)

    def test_prefers_newline_before_limit(self):
        text = "First line stays within limit\nSecond line continues after limit"

        chunks = bot.split_discord_message(text, limit=40)

        self.assertEqual(2, len(chunks))
        self.assertEqual("First line stays within limit", chunks[0])
        self.assertEqual("Second line continues after limit", chunks[1])

    def test_handles_long_text_with_only_spaces(self):
        text = " " * 25

        chunks = bot.split_discord_message(text, limit=10)

        self.assertEqual(1, len(chunks))
        self.assertEqual("", chunks[0])

    def test_hard_split_on_long_word(self):
        text = "a" * 25

        chunks = bot.split_discord_message(text, limit=10)

        self.assertEqual(["a" * 10, "a" * 10, "a" * 5], chunks)

    def test_strips_trailing_whitespace_in_intermediate_chunks(self):
        text = "chunk1 trailing   \nchunk2 trailing   \nchunk3 trailing   \nchunk4"

        chunks = bot.split_discord_message(text, limit=25)

        self.assertEqual(3, len(chunks))
        self.assertEqual("chunk1 trailing", chunks[0])
        self.assertEqual("chunk2 trailing", chunks[1])
        self.assertEqual("chunk3 trailing   \nchunk4", chunks[2])


class ResponseFormattingLimitTests(unittest.TestCase):
    def test_formatted_messages_stay_within_limit_without_exit_prefix(self):
        header = bot.MESSAGE_HEADER
        limit = bot.DISCORD_MESSAGE_LIMIT
        chunk_limit = max(1, limit - len(header))
        response = "a" * limit

        chunks = bot.split_discord_message(response, limit=chunk_limit)

        for chunk in chunks:
            formatted = f"{header}{chunk}"
            self.assertLessEqual(len(formatted), limit)

    def test_formatted_messages_stay_within_limit_with_exit_prefix(self):
        header = bot.MESSAGE_HEADER
        limit = bot.DISCORD_MESSAGE_LIMIT
        chunk_limit = max(1, limit - len(header))
        response = "a" * limit
        prefix = "[exit 42] "

        chunks = bot.split_discord_message(prefix + response, limit=chunk_limit)

        for chunk in chunks:
            formatted = f"{header}{chunk}"
            self.assertLessEqual(len(formatted), limit)


class IsCooldownOkTests(unittest.TestCase):
    def setUp(self):
        self._original_last_user_ask_at = dict(bot.last_user_ask_at)
        bot.last_user_ask_at.clear()

    def tearDown(self):
        bot.last_user_ask_at.clear()
        bot.last_user_ask_at.update(self._original_last_user_ask_at)

    def test_first_call_allows_and_records_timestamp(self):
        guild_id = 123
        user_id = 456
        now = 100.0

        allowed = bot.is_cooldown_ok(guild_id, user_id, now)

        self.assertTrue(allowed)
        self.assertEqual(now, bot.last_user_ask_at[(guild_id, user_id)])

    def test_immediate_second_call_is_blocked(self):
        guild_id = 123
        user_id = 456
        now = 100.0

        first_allowed = bot.is_cooldown_ok(guild_id, user_id, now)
        second_allowed = bot.is_cooldown_ok(guild_id, user_id, now)

        self.assertTrue(first_allowed)
        self.assertFalse(second_allowed)
        self.assertEqual(now, bot.last_user_ask_at[(guild_id, user_id)])

    def test_call_after_cooldown_is_allowed_and_updates_timestamp(self):
        guild_id = 123
        user_id = 456
        first_ts = 100.0
        second_ts = first_ts + bot.PER_USER_COOLDOWN_SEC

        bot.is_cooldown_ok(guild_id, user_id, first_ts)
        allowed_after_cooldown = bot.is_cooldown_ok(guild_id, user_id, second_ts)

        self.assertTrue(allowed_after_cooldown)
        self.assertEqual(second_ts, bot.last_user_ask_at[(guild_id, user_id)])


class PowershellPrefixTests(unittest.TestCase):
    @patch("ai.bot.shutil.which")
    def test_prefers_pwsh_when_available(self, mock_which):
        mock_which.side_effect = lambda exe: "/usr/bin/pwsh" if exe == "pwsh" else None

        result = bot.powershell_prefix()

        self.assertEqual(
            ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass"],
            result,
        )

    @patch("ai.bot.shutil.which")
    def test_falls_back_to_powershell_when_pwsh_missing(self, mock_which):
        mock_which.side_effect = lambda exe: None if exe == "pwsh" else "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

        result = bot.powershell_prefix()

        self.assertEqual(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass"],
            result,
        )

    @patch("ai.bot.shutil.which", return_value=None)
    def test_raises_when_no_powershell_available(self, mock_which):
        with self.assertRaises(FileNotFoundError):
            bot.powershell_prefix()


class AskAiAsyncTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_kills_and_reaps_process(self):
        class DummyProc:
            def __init__(self):
                self.killed = False
                self.wait = AsyncMock(return_value=0)
                self.communicate = AsyncMock(return_value=(b"", None))

            def kill(self):
                self.killed = True

        dummy_proc = DummyProc()

        async def fake_create_subprocess_exec(*_args, **_kwargs):
            return dummy_proc

        async def fake_wait_for(awaitable, timeout):
            if hasattr(awaitable, "close"):
                awaitable.close()
            raise asyncio.TimeoutError

        with patch("ai.bot.os.path.isfile", return_value=True), \
            patch("ai.bot.powershell_prefix", return_value=[]), \
            patch("ai.bot.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec), \
            patch("ai.bot.asyncio.wait_for", new=fake_wait_for):
            with self.assertLogs("nightshade-bot", level="WARNING") as cm:
                message, code = await bot.ask_ai_async("hello")

        self.assertIn("timed out", message)
        self.assertEqual(code, 124)
        self.assertTrue(dummy_proc.killed)
        self.assertEqual(dummy_proc.wait.await_count, 1)
        self.assertIn("timed out", " ".join(cm.output).lower())


class AskAiAsyncErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_unexpected_exception_logs_details_and_hides_message(self):
        async def fake_create_subprocess_exec(*_args, **_kwargs):
            raise RuntimeError("boom")

        with patch("ai.bot.os.path.isfile", return_value=True), \
            patch("ai.bot.powershell_prefix", return_value=[]), \
            patch("ai.bot.asyncio.create_subprocess_exec", new=fake_create_subprocess_exec):
            with self.assertLogs("nightshade-bot", level="ERROR") as cm:
                message, code = await bot.ask_ai_async("hello")

        self.assertEqual("⚠️ Error calling AI. Please try again later.", message)
        self.assertEqual(1, code)
        self.assertNotIn("boom", message)
        self.assertIn("boom", " ".join(cm.output))


class ConfigEnvironmentOverrideTests(unittest.TestCase):
    def tearDown(self):
        importlib.reload(bot)

    def test_ai_name_override_updates_message_header(self):
        with patch.dict(os.environ, {"AI_NAME": "CustomAI"}, clear=False):
            importlib.reload(bot)
            self.assertEqual("CustomAI", bot.AI_NAME)
            self.assertTrue(bot.MESSAGE_HEADER.startswith("🤖 CustomAI:"))

    def test_max_questions_override(self):
        with patch.dict(os.environ, {"MAX_QUESTIONS_PER_SERVER": "123"}, clear=False):
            importlib.reload(bot)
            self.assertEqual(123, bot.MAX_QUESTIONS_PER_SERVER)

    def test_ai_timeout_override(self):
        with patch.dict(os.environ, {"AI_TIMEOUT_SEC": "12.5"}, clear=False):
            importlib.reload(bot)
            self.assertEqual(12.5, bot.AI_TIMEOUT_SEC)

    def test_per_user_cooldown_override(self):
        with patch.dict(os.environ, {"PER_USER_COOLDOWN_SEC": "7"}, clear=False):
            importlib.reload(bot)
            self.assertEqual(7.0, bot.PER_USER_COOLDOWN_SEC)

    def test_thinking_message_override(self):
        with patch.dict(os.environ, {"THINKING_MESSAGE": "processing"}, clear=False):
            importlib.reload(bot)
            self.assertEqual("processing", bot.THINKING_MESSAGE)


if __name__ == "__main__":
    unittest.main()
