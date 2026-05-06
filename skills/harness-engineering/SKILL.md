---
name: harness-engineering
description: Use when improving a codebase for agent legibility, setting up agent workflows, designing AGENTS.md files, eliminating AI slop via linting, or structuring repos for autonomous coding agent delegation. Triggers on tasks involving agent-first development, coding agent optimization, or scaling engineering throughput with agents.
---

# Harness Engineering

Patterns for making codebases legible to coding agents and scaling engineering
throughput through agent delegation. Full source transcripts are in
`references/`.

The goal is a codebase where agents autonomously produce acceptable code
without human intervention.

## Agentic Legibility Scorecard

Score a repository across these seven metrics (each 0-3, max 21):

### 1. Bootstrap Self-Sufficiency
Can an agent clone the repo and get a working environment with zero external
knowledge? Look for: setup scripts, dependency declarations, env templates,
seed data.

### 2. Task Entry Points
Is it obvious how to run common operations? Look for: `make`, `just`, or
script-based commands for build, test, lint, deploy. Agents need discoverable
entry points, not tribal knowledge.

### 3. Validation Harness
Can the agent check whether its changes work? Fast test suites, type checking,
snapshot tests. If the agent cannot tell whether its own work is correct, you
are back to reviewing everything by hand.

### 4. Linting and Formatting
Linting is the highest-leverage, lowest-effort improvement. Agents can check
their work cheaply and catch violations before humans see them. Formatters
eliminate style noise from diffs. Vibe-code new lint rules to ban specific
anti-patterns you observe.

### 5. Codebase Map
Is there a navigation aid? AGENTS.md, directory-level READMEs, or structured
doc trees that help the agent understand what lives where.

### 6. Doc Structure
Are docs organized close to the code they describe? Progressive disclosure:
short pointers in AGENTS.md, detailed docs in subdirectories. The agent should
not need to page in a 500-line doc to find the one paragraph it needs.

### 7. Decision Records
Is there a record of why things are the way they are? ADRs, `.notes/`
directories, or commit messages that explain intent. Without these, agents (and
new humans) repeat past mistakes.

## AGENTS.md Philosophy

Keep it lean. The agent should decide what to do, not be over-instructed.

**What to include:**
- How to run tests and which tests matter most
- Build/lint/deploy commands that aren't obvious from the repo structure
- Conventions the agent wouldn't infer from reading code (e.g., "one hook per
  file," "use the blessed crypto library, not arbitrary npm packages")
- Pointers to reference docs, not the docs themselves

**What to omit:**
- Anything the agent can derive from reading the code
- Duplicative descriptions of the architecture (code is the source of truth)
- Tens of pages of instructions (diminishing returns; biases the agent away
  from forming its own judgment)

**Hierarchy for larger codebases:**
- Root AGENTS.md: cross-cutting standards
- Module-level AGENTS.md: domain-specific instructions scoped to that directory
- Skills: reusable workflows for recurring tasks (making PRs, doing code review,
  landing changes)
- Sub-agents: specialists for verification and enforcement

Well-named files and folders matter more than documentation. When the agent
searches the codebase, discoverability through naming is the first signal.

## Eliminating AI Slop

"AI slop" is code you don't like. If you can articulate what you don't like,
you can encode it as a constraint that prevents it from entering the codebase.

### Custom Lint Rules

Vibe-code ESLint (or equivalent) rules to statically disallow specific
anti-patterns. Example from OpenAI's team: agents kept creating duplicate
bounded-concurrency helpers across the codebase, but only the canonical one in
`async-utils` was instrumented with OpenTelemetry. Solution: a lint rule that
bans defining that function signature anywhere except the canonical package.

Pattern:
1. Observe a class of misbehavior in agent output
2. Write a lint rule that bans it
3. Have agents write exhaustive positive/negative test cases for the rule
4. The rule now prevents that class of slop across all future agent runs

These lint rules stack: each team member adds rules for anti-patterns they
catch, and everyone's agents benefit.

### Reviewer Sub-Agents

Create bespoke code reviewer agents that enforce non-functional requirements.
Types that work well:
- **Standards enforcer**: checks code against your style/architecture docs
- **Reliability reviewer**: checks for missing retries, timeouts, error handling
  on network calls
- **Security reviewer**: checks for use of blessed crypto libraries, secure
  interfaces
- **Product QA reviewer**: generates manual QA plans based on product specs,
  checks that changes don't break user journeys

These reviewer agents leave comments on PRs that the authoring agent is forced
to address.

## Progressive Disclosure for Documentation

For large codebases, context is too large for a single AGENTS.md. Structure it
as progressive disclosure:

```
docs/
├── security.md          # 250 lines on security best practices
├── reliability.md       # retries, timeouts, circuit breakers
├── frontend-arch.md     # component patterns, hook conventions
└── api-conventions.md   # endpoint patterns, error formats
```

AGENTS.md contains short pointers: "For security practices, read
`docs/security.md`." The agent pages in the specific doc it needs for the
current task, not all docs for every task.

Skills work the same way: short description in frontmatter triggers loading,
full instructions only when invoked. Invest in high-quality descriptions so the
agent knows when to invoke each skill.

## Team Knowledge Flywheel

Each engineer who joins a team brings different expertise. When they encode that
expertise into the codebase (lint rules, docs, reviewer agents, skills), every
other engineer's agents improve.

Example: a backend-focused engineer couldn't get high-quality React output.
When a front-end architect joined and encoded their patterns (one hook per file,
small composable components, snapshot testing), everyone's agents started
producing better front-end code.

This flywheel compounds: early investment in building blocks (lint rules, test
infrastructure, doc standards) yields 3-10x throughput per engineer once the
system matures.

## Decision History with .notes

Commit messages capture what changed but not why decisions were made during a
session. `.notes/` is a directory where the agent writes decision rationale as
it works, independent of commits. This creates a history you can consult when
revisiting code months later: "why was it implemented this way?"

Pair this with specs that live in the repo, not in Slack threads or external
tools. When the context behind a decision is in the codebase, agents (and new
team members) can find it.

## Work Trees for Parallel Development

Use git worktrees to run multiple agent sessions on the same repo without
stepping on each other's changes. Each worktree is an isolated checkout on its
own branch.

## Episodic Memory via Archived Trajectories

Keep previous iterations of completed tasks in an archive folder within the
repo. When the agent starts a similar task, it can read previous trajectories
to learn what worked and what didn't -- episodic memory without special
infrastructure.

## Test-Driven Development with Agents

Write tests first (or have the agent write them from a product spec), then
have the agent implement code to pass them. This gives the agent a clear
self-verification loop for long-running sessions without human intervention.

## Full Automation: Ticket to Merge

The end state of harness engineering is an orchestrator that manages the
full lifecycle:
1. Pull a ticket from the issue tracker (e.g., Linear)
2. Spin up the agent in a work tree
3. Agent implements the code
4. Put it up for review (CI + agentic code reviewers)
5. Go back and forth with reviewers until constraints are satisfied
6. Only bring the human in for a final yes/no merge decision

This removes humans from writing code entirely and moves them to prioritizing
work, reviewing work, and refining constraints. The key enabler is having
enough guardrails (lint rules, tests, reviewer agents) that the automated loop
reliably produces acceptable code.

## Automations for Recurring Work

Schedule recurring agent tasks:
- Review all open PRs for merge conflicts (daily)
- Summarize git history for standup (morning)
- Check Slack for action items and update to-dos
- Run the test suite against main and report failures

These are lightweight cron-like tasks that keep the codebase healthy without
human attention.

## The Minimal Tools Principle

Fewer powerful tools > many specialized ones, so agents figure out how without
being overly constrained. Example: the Codex team gives the agent a terminal
tool (not individual read/write/search tools) and lets it choose standard Unix
commands. The exception is security: sandboxing constrains what the agent can
do (folder read/write permissions, network access), but within those
constraints, the agent has full freedom.

## Applying to a Brownfield Codebase

For existing repos without agent infrastructure:

1. **Start with linting.** Turn on all available linters. Vibe-code new rules
   for patterns you don't want.
2. **Add AGENTS.md.** Start with build/test/lint commands and a handful of
   key conventions. Keep it under 50 lines initially.
3. **Carve apart business domains.** Add interfaces between modules, add
   local documentation for each domain's best practices.
4. **Write the acceptance criteria down.** Sit with your team and rapid-fire
   bullet points about what "good code" looks like for your project. Security,
   reliability, component architecture. Get a few files in the codebase with
   the seeds of these standards.
5. **Iterate.** Each time you reject agent output, ask: "Can I encode this
   rejection as a lint rule, test, or doc?" If yes, do it. The system improves
   with every rejection.
