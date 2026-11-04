# Contributing

Contributions are published under the MIT License. Before a technique joins this repository, it must meet these rules:

1. **It runs on its own.** It works right after install, and depends on nothing unpublished.
2. **It has tests.** New scripts have tests in `tests/`. Anything that needs a paid service says clearly what is not tested automatically.
3. **It is a general rule.** Write when it applies, what to do and why, not the production history of one film.
4. **It works everywhere.** It supports Claude Code, Codex and Kimi Code, with paths relative to `SKILL.md` and no tool-specific variables.
5. **It is written in English.** Skills tell the agent to talk to people in their own language.

Never add:

- Names or material from third-party works and characters
- Tools that get around any site's login, captcha, regional limits or terms of service
- Keys or personal paths
- Images, audio or video without cleared rights. Cleared original demos go in `docs/`

Before you commit, run:

```bash
python scripts/check_public.py
python -m unittest discover -s tests
claude plugin validate .
```

Skill names use the `dula-` prefix so they don't clash with skills people already have.
