# skills

> Open-source agent skills from [Temi](https://usetemi.com). Works with Claude Code, Claude Cowork, Codex, Cursor, Gemini CLI, and anything else that supports the [Agent Skills](https://agentskills.io) spec.

## Install

### Claude Code

```bash
/plugin marketplace add usetemi/skills
/plugin install usetemi@usetemi
```

### skills.sh (Codex, Cursor, Gemini CLI, 37+ others)

```bash
npx skills add usetemi/skills
```

### Claude Cowork / Claude Desktop

Each skill ships as a zip on the [latest release](https://github.com/usetemi/skills/releases/latest). Download the one you want and upload it via **Settings → Capabilities → Skills**.

## What's inside

| Skill | What it does |
|---|---|
| [`google-analytics`](skills/google-analytics) | Query GA4 reports, manage properties, streams, key events, audiences, and access bindings, and send Measurement Protocol events. Wraps the Data API, Admin API, and MP via the `ga4` CLI. |
| [`google-drive`](skills/google-drive) | Sync Google Drive files with a manifest-tracked pull/push workflow. Re-imports Google Docs, Sheets, and Slides as native format on push. Works with shared drives. Wraps `rclone`. |
| [`google-search-console`](skills/google-search-console) | Query Search Console analytics, inspect URL indexing, manage sitemaps, and run PageSpeed Insights audits. Wraps the GSC and PageSpeed APIs via the `gsc` CLI. |
| [`harness-engineering`](skills/harness-engineering) | Make codebases legible to coding agents — agentic legibility scorecard, AGENTS.md design, AI slop elimination via custom lint rules, reviewer sub-agents, and the ticket-to-merge automation loop. |
| [`humanize`](skills/humanize) | Remove signs of AI-generated writing from text. 29 patterns from Wikipedia's "Signs of AI writing" guide, plus voice calibration and a final anti-AI audit pass. Forked from [blader/humanizer](https://github.com/blader/humanizer). |
| [`pr-video-receipts`](skills/pr-video-receipts) | Set up Playwright `page.screencast` recordings of agent-driven smoke tests, uploaded as GitHub draft release assets and embedded inline in PR comments — automatic video evidence on every PR, garbage-collected on close. |

Each skill folder is self-contained. `SKILL.md` is the entry point, with `references/` for deeper docs the agent loads on demand.

## License

MIT. See [LICENSE](LICENSE).

## About Temi

These skills come out of work at [Temi](https://usetemi.com). We open-source the parts of our agent toolkit that we find generally useful.

If you build something with them, we'd love to hear about it.
