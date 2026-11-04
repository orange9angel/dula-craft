# Quickstart

Goal: your first 20–30 second film. Most of the time goes to waiting for images. Your job is to look and decide.

## Before you start

- dula-craft is installed (see the [README](../README.md)).
- You have one AI tool: Claude Code, Codex or Kimi Code.
- For automatic images, install and sign in to [Codex CLI](https://github.com/openai/codex). Otherwise, you make the images yourself.
- For voices, have audio files ready or [set up a voice key](configuration.md#voices). You can also start with a silent draft.

## Step 1: Share your idea

Open your AI tool and say:

> Make me an animated short

It asks three things: the story, the length, and where the voices come from. No idea yet? It will suggest a few original ones.

**Please use original characters.** Publishing a film with characters from existing shows, comics or games can infringe copyright.

## Step 2: Approve the character designs

The agent draws each character and shows you. This is the most important decision in the film, because every later drawing follows these designs.

If something is off, just say so: "bigger head" or "make the raincoat yellow".

## Step 3: Watch a 20-second test

Next, the agent draws poses and mouths, adds voices and shows you a short test. While you watch, ask yourself:

- Is it the same character in every shot, with the same face and body?
- Do mouths move when characters talk?
- Do characters in a conversation face each other?
- Can you hear every line? Do the jokes land?

## Step 4: Make the full film

Once you like the test, the agent finishes the film, checks the mouths automatically and hands it over. Your film is `output/film.mp4` in the film folder.

## Step 5 (optional): Add subtitles and a title card

> Add English and French subtitles to this film

> Add an ink-style opening title card that says "..."

## What's in a film folder

```text
my_film/
├── story.md      The story
├── config/       Shots and settings. film.json is the main one
├── assets/       All the drawings
├── audio/        Voices, sound effects and music
├── build/        Working files and review images. Safe to delete
└── output/       The finished film
```

To adjust shots by hand, see the [film.json reference](../skills/dula-flat-cel/references/film-json.md).

## Something went wrong?

See the [FAQ](faq.md), or paste the error to your agent.
