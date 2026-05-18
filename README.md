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
| [`ask-clarifying-questions`](skills/ask-clarifying-questions) | Run a structured interview before writing code — surface load-bearing assumptions in rounds of up to 4 questions, predict before asking, and stop on alignment, not count. Uses `AskUserQuestion` in Claude Code, `request_user_input` in Codex, plain prose as fallback. |
| [`fly-io`](skills/fly-io) | Deploy, configure, troubleshoot, and architect Fly.io apps with production-grade defaults for flyctl, fly.toml, Machines, networking, volumes, Managed Postgres, Tigris, Redis, LiteFS, extensions, CI/CD, and Fly-specific gotchas. |
| [`google-analytics`](skills/google-analytics) | Query GA4 reports, manage properties, streams, key events, audiences, and access bindings, and send Measurement Protocol events. Wraps the Data API, Admin API, and MP via the `ga4` CLI. |
| [`google-drive`](skills/google-drive) | Sync Google Drive files with a manifest-tracked pull/push workflow. Re-imports Google Docs, Sheets, and Slides as native format on push. Works with shared drives. Wraps `rclone`. |
| [`google-search-console`](skills/google-search-console) | Query Search Console analytics, inspect URL indexing, manage sitemaps, and run PageSpeed Insights audits. Wraps the GSC and PageSpeed APIs via the `gsc` CLI. |
| [`harness-engineering`](skills/harness-engineering) | Make codebases legible to coding agents — agentic legibility scorecard, AGENTS.md design, AI slop elimination via custom lint rules, reviewer sub-agents, and the ticket-to-merge automation loop. |
| [`humanize`](skills/humanize) | Remove signs of AI-generated writing from text. 29 patterns from Wikipedia's "Signs of AI writing" guide, plus voice calibration and a final anti-AI audit pass. Forked from [blader/humanizer](https://github.com/blader/humanizer). |
| [`node-26`](skills/node-26) | Upgrade and modernize Node.js projects for Node.js 26: Temporal, Map/WeakMap get-or-insert helpers, Iterator.concat, raw crypto key formats, removed APIs, and Current vs LTS rollout guidance. |
| [`pdf`](skills/pdf) | Fill, redline, and generate PDFs with the right tool for the source. Auto-detects AcroForm vs flat PDFs, handles AES-encrypted government forms, navigates appearance-stream gotchas (`/NeedAppearances`, `/Ch` comboboxes, `/Sig` widgets, multi-page header carry-forward), and verifies output by rendering. |
| [`pr-video-receipts`](skills/pr-video-receipts) | Set up Playwright `page.screencast` recordings of agent-driven smoke tests, uploaded as GitHub draft release assets and embedded inline in PR comments — automatic video evidence on every PR, garbage-collected on close. |
| [`tailscale`](skills/tailscale) | Work across the Tailscale platform: connectivity, grants and ACLs, MagicDNS, Serve, Funnel, Services, app connectors, subnet routers, exit nodes, SSH, Kubernetes, containers, CI/CD automation, API/OAuth workflows, and production diagnostics. |

Each skill folder is self-contained. `SKILL.md` is the entry point, with `references/` for deeper docs the agent loads on demand.

## License

MIT. See [LICENSE](LICENSE).

## About Temi

These skills come out of work at [Temi](https://usetemi.com). We open-source the parts of our agent toolkit that we find generally useful.

If you build something with them, we'd love to hear about it.
