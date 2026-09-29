# Skills Repository

`usetemi/skills` publishes Temi agent skills for coding agents and tools that
support the Agent Skills spec. Keep this file focused on instructions agents need
while changing the repo; keep public install, catalog, and distribution copy in
`README.md`.

## Orientation

- Each skill is self-contained under `skills/<name>/`. `SKILL.md` is the required
  entry point; deeper references should live inside the skill and be loaded only
  when the task calls for them.
- `README.md` is the canonical public catalog and install guide. Update it when a
  skill is added, removed, renamed, or its public description changes.
- Plugin and marketplace metadata lives under `.claude-plugin/`,
  `.codex-plugin/`, and `.agents/plugins/`. Touch those files only for registration
  or metadata changes.

## Skill Changes

- When adding a new skill, create `skills/<name>/SKILL.md` and keep the skill
  directory self-contained.
- Register new skills in `.claude-plugin/marketplace.json` and add a row to the
  `README.md` skill table.
- Codex discovers skills from `./skills/` via `.codex-plugin/plugin.json`, so new
  skills do not need per-skill Codex registration unless root plugin metadata
  changes.
- Do not document capabilities that are not implemented in the skill.

## Validation

- For docs-only edits, re-read the changed guidance and check for duplicated
  README content, stale file indexes, or command drift.
- Before finishing, run `git diff --check`.
