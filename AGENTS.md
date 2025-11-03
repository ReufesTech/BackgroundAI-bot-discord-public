# Repository Guidelines

## Documentation parity
- Whenever you add or modify a feature, update any related documentation (README files, inline docs, or usage notes) in the same change.
- If a change does not require documentation updates, explain why in the pull request description.

## Required validation
- Before committing, run the project test suite most relevant to your changes. At minimum, execute `pytest ai/test_bot.py` and resolve any failures.
- Include the exact commands you ran in your pull request message under a **Testing** section.

## Pull request message conventions
- Start the PR title with a concise summary in imperative mood (e.g., "Add", "Fix", "Update").
- Structure the PR body with:
  - A **Summary** section listing key changes as bullet points.
  - A **Testing** section enumerating the validation commands you ran and their outcomes.
- Reference documentation updates (or the rationale for none) within the **Summary** section.
