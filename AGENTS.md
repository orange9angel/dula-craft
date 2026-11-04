# Working in this repository

This is a public repository. Everything committed here can be seen and copied by anyone, and history is hard to take back.

New techniques are added when a real film needs them, not in advance. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for what belongs here.

## Before adding anything from another source

Do this every time, whether the source is a private project, an old film, another repository or the web. **Write the source's content again as a general rule or as new code.** Don't paste it in. Then check each item, and stop if any fails:

| Check | What to confirm |
|---|---|
| **License** | Any code, data, prompt, model or asset you reuse allows this use under MIT, and its notice is kept. No license means no permission. New dependencies are listed in `docs/licenses.md` |
| **Privacy** | No names, emails, account or organization IDs, bucket names, personal paths, internal project names or quotes from private conversations |
| **Secrets** | No keys, tokens, cookies or login state, anywhere in the files or the commits being pushed |
| **Copyright** | No third-party characters, titles, creators, or material taken from them, including in file names, examples, comments and measurements. No media without cleared rights |
| **Platform terms** | Nothing that automates or gets around a site's login, captcha, regional limits or terms of service |
| **Stands alone** | It runs after a clean install, with nothing unpublished, and works with Claude Code, Codex, Kimi Code and Qoder |

Then run the checks, and don't push if any fails:

```bash
python scripts/check_public.py
python -m unittest discover -s tests
claude plugin validate .
```

`check_public.py` catches patterns, not meaning, so read the full diff yourself as well. In your report, say what you extracted, the result of each check above, and what you could not verify. If you're unsure about a license or a right, ask the person. Don't guess.

## Other rules

- Write skills and guides in English, and tell agents to talk to people in their own language.
- Keep films out of this repository, except cleared demos in `docs/`.
- Before saying something works, try it the way a user would: open the page, play the video, run the command from a clean install.
