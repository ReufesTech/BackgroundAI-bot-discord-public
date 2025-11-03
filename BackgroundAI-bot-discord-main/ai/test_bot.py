import os
import sys
import types
import unittest
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
