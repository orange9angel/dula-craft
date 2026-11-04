# FAQ

Didn't find your answer? Ask in [Discussions](https://github.com/orange9angel/dula-craft/discussions).

## Installing

**My agent can't find the skill.**
Quit your AI tool completely and open it again. A running session may not see newly installed skills.

**Qoder doesn't list the skills.**
In a running Qoder CLI session, run `/skills reload`. Qoder CLI finds them through `~/.agents/skills`. This has been checked with Qoder CLI, but not with Qoder IDE.

**It says git, Python or ffmpeg is missing.**
See [required software](configuration.md#required-software). Open a new terminal after installing.

**The installer says "Skipped... something else is already there".**
Something with that name already exists, and the installer won't overwrite it. Rename or move it, then install again.

**`install.sh` fails in Git Bash.**
On Windows, use the PowerShell command instead.

## Images

**Can I use this without Codex CLI?**
Yes. The list of images is in `build/images_todo.md`. Make them with any tool, save them to the listed paths, and run the same command again.

**Codex says I've run out of quota.**
Run the command again once your quota is back. Finished images are skipped, so they don't use quota twice.

**A character looks different from one drawing to the next.**
First make sure you're happy with the character design. Then ask your agent to delete and redraw the drawings that don't match. Rejected drawings should never be used as references.

**A cutout has leftover background or a missing piece.**
Open `build/check_alpha.png`. Everything is shown on magenta, so problems stand out. Ask your agent to redraw that one.

## Mouths and sound

**It says "Frozen mouth".**
A character is talking, but that drawing has no mouth variants. Ask your agent to add them. If it's deliberate, such as one long scream, it can be marked as an exception.

**The mouth stays open or barely moves.**
Run `check_mouths.py` to see the drawing changes for each line. The audio may be muffled, or there may be only one mouth variant.

**It says "Key rejected, or Audio Generation 1.0 is not enabled".**
Check that the service is enabled and that the key came from the speech console. See [Voices](configuration.md#voices).

**There's a constant hiss.**
The ambience clip is usually just noise. Try a different one.

## Results and use

**What kind of film is this good for?**
Short films with simple character designs, driven by dialogue and expressions. It isn't a good fit for complex fights, long continuous action or realistic styles.

**How long does a film take?**
Mostly it depends on image speed. An image usually takes 1–2 minutes, and a 30-second film usually needs a few dozen.

**Can I use it commercially?**
This project's MIT License allows it. Third-party services and materials have their own terms. See [Licensing and rights](licenses.md).

**Is my data uploaded?**
This project collects nothing. See [Privacy](../README.md#privacy).
