# AI Module Guidelines

## Python async code
- Keep functions coroutine-friendly: prefer `async`/`await` patterns and avoid blocking calls inside `async` functions.
- When introducing new concurrency primitives, ensure they integrate cleanly with `asyncio` (e.g., use `asyncio.create_task` rather than threading).

## PowerShell scripts
- Maintain compatibility with PowerShell 7 (`pwsh`) and fall back gracefully for Windows PowerShell where needed.
- Test script changes on both Unix-like and Windows-compatible paths when possible.

## Testing requirements
- The primary regression tests live in [`ai/test_bot.py`](./test_bot.py). Run `pytest ai/test_bot.py` after modifying Python or PowerShell logic.
- Any updates to `ai/bot.py` or `BackgroundAI_Bot.ps1` must include corresponding test coverage or updates in [`ai/test_bot.py`](./test_bot.py) to exercise the new behavior.

## Style and structure
- Keep logging via the existing `nightshade-bot` logger consistent; new log entries should use the same logger.
- Document tricky logic with concise comments near the relevant code, and mirror noteworthy behavior in `test_bot.py`.
