# humanize — upstream sync

This skill is imported from [blader/humanizer](https://github.com/blader/humanizer) (MIT, © Siqi Chen). `usetemi/humanizer` is a fork that tracks upstream verbatim.

## Updating from upstream

Run from the repo root:

```bash
cd /tmp && rm -rf humanizer-upstream
git clone --depth 1 https://github.com/blader/humanizer humanizer-upstream
diff humanizer-upstream/SKILL.md <repo>/skills/humanize/SKILL.md
```

Review the diff and port changes into `SKILL.md` **while preserving the usetemi customizations** listed below. Do not blindly overwrite.

## Customizations to preserve

When merging upstream changes, keep these local edits:

1. **Frontmatter** — only `name` and `description`. Upstream ships `version`, `license`, `compatibility`, `allowed-tools`; strip them.
2. **Skill name** — `humanize` (not `humanizer`). Invocation surface is `/humanize`.
3. **Description** — a single-line description with explicit trigger phrases ("humanize this", "make this sound human", "remove AI-isms", `/humanize`). If upstream expands the pattern list, mirror the new patterns into our description; otherwise leave the trigger wording alone.
4. **PERSONALITY AND SOUL** — lives in `references/personality-and-soul.md`. The SKILL.md body has a short pointer in its place and a cross-reference from the Voice Calibration fallback. If upstream edits that section, update the reference file, not SKILL.md.
5. **Attribution footer** — the "Originally authored by Siqi Chen..." line at the bottom of SKILL.md. Keep it.
6. **LICENSE** — MIT attribution to Siqi Chen. Re-copy if upstream changes their LICENSE file.

## Upstream additions to watch for

- **New patterns** — upstream numbers them (currently 1–29). If the count grows, add new sections in SKILL.md, add the new pattern names to the description's trigger list, and bump the count in this repo's top-level `README.md` row.
- **New sections** (like PERSONALITY AND SOUL was) — decide whether to keep inline or extract to `references/`. The rule of thumb: extract if the section is >30 lines or is narratively separable from the pattern catalogue.
- **Frontmatter changes** — upstream may add more fields; keep stripping to `name` + `description`.

## Registration — no changes needed on update

Unless the skill name changes, `.claude-plugin/marketplace.json` and the top-level `README.md` skills table don't need updates on a normal upstream sync.

## Note on this README

Skills in `usetemi/skills` generally don't ship a `README.md` (see `AGENTS.md` — "No auxiliary files"). This one is an exception because the skill is a fork of an external project and the sync workflow isn't obvious from code alone.
