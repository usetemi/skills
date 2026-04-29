# Skills Repository

`usetemi/skills` is an open-source repository of agent skills published by [Temi](https://usetemi.com). Skills extend AI agents (Claude Code, Claude Cowork, Codex, Cursor, Gemini CLI, and others that support the [Agent Skills spec](https://agentskills.io)) with specialized knowledge, workflows, and tools.

This repo serves both as:
- A **Claude Code plugin marketplace** (`/plugin marketplace add usetemi/skills`)
- A **skills.sh-compatible** package (`npx skills add usetemi/skills`)

## Repository Structure

```
skills/
├── .claude-plugin/
│   └── marketplace.json    # Claude Code marketplace configuration
├── .github/workflows/
│   ├── release.yml         # Per-skill zip artifacts on tag push
│   └── copier-drift.yml    # Fails PRs where rendered files diverge from template/
├── skills/                 # All skills live here
│   └── <skill-name>/
│       ├── SKILL.md        # Required entry point
│       └── .copier-answers.yml  # (google-* skills) Copier substitutions for templated modules
├── template/
│   ├── SKILL.md            # Starting template for new skills
│   ├── copier.yml          # Copier template config — see template/AGENTS.md
│   └── src/{{ pkg }}/      # Jinja templates rendered into each consuming skill
└── AGENTS.md               # This file (shared agent instructions)
```

## Shared modules across the google-* skills

`template/` is also a [Copier](https://copier.readthedocs.io/) template that renders shared modules (`__init__.py`, `__main__.py`, `auth.py`) into each google-* skill. Each consuming skill carries a `.copier-answers.yml` recording its substitution values; running `copier update --defaults --trust` from a skill's directory regenerates the templated files from the current template state.

Edit templates under `template/src/{{ pkg }}/`, run `copier update` in each consuming skill, and commit both the template change and the regenerated outputs. `.github/workflows/copier-drift.yml` enforces this on PRs. Detailed authoring guide: [`template/AGENTS.md`](template/AGENTS.md).

## Creating a new skill

Use Anthropic's `skill-creator` for the design, structure, and validation workflow:

```bash
npx skills add https://github.com/anthropics/skills --skill skill-creator
```

References:
- [skills.sh/anthropics/skills/skill-creator](https://skills.sh/anthropics/skills/skill-creator)
- [SKILL.md source](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

After scaffolding, register the new skill in this repo: add its path to the `skills` array in `.claude-plugin/marketplace.json` and add a row to the table in `README.md`.

## Releasing

A `v*` tag (e.g. `v0.1.0`) triggers `.github/workflows/release.yml`, which zips each `skills/*` directory and attaches the zips to a GitHub Release. Cowork/Desktop users download the zip they want.

## Distribution

```bash
# Claude Code plugin marketplace
/plugin marketplace add usetemi/skills
/plugin install skills@usetemi

# skills.sh (Codex, Cursor, Gemini CLI, etc.)
npx skills add usetemi/skills
```
