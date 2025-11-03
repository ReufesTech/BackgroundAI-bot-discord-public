import asyncio
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


if __name__ == "__main__":
    unittest.main()
