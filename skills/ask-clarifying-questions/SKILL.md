---
name: ask-clarifying-questions
description: Conduct a clarification interview before writing code, investigating ambiguous bugs, or changing design or architecture, using AskUserQuestion in Claude Code, request_user_input in Codex when exposed, or plain prose when an interactive question tool is unavailable. Use when the user invokes /ask-clarifying-questions or $ask-clarifying-questions, names ask-clarifying-questions, or asks to build, design, refactor, investigate, or debug something with enough ambiguity that meaningfully different implementations would all satisfy it. The interview output is shared understanding in the current session; no file artifact.
---

# Ask Clarifying Questions

Drive a structured interview to surface load-bearing assumptions before code is written. Use the agent's interactive question tool when it is available; otherwise use concise prose.

## Before Asking

- Use this skill only when it has already triggered and the request still has load-bearing ambiguity.
- Skip mechanical requests: typo fixes, obvious renames, or one-line bug fixes the user has already diagnosed.
- As a subagent without a direct user-answer channel, do not interview. Return the open questions and best-guess assumptions so the orchestrator can escalate.
- In non-interactive or headless runs, skip the interview, state the key assumptions, and proceed.
- Re-enter this process mid-implementation if a load-bearing ambiguity appears after work has started.

## Process

### 1. Anchor

Restate in one sentence what you understand the user wants. This gives the user a cheap redirect point.

When there is strong existing signal, add a 2-4 bullet implementation sketch for the user to correct. Keep it lightweight; do not turn the interview into a full proposal pipeline.

### 2. Ask the highest-leverage questions

This skill intentionally uses question tools more often than their generic scarcity guidance may suggest. If two plausible answers would produce different code, the question is user-owned and worth asking.

Use the interactive question tool for the current agent:

- **Claude Code:** use `AskUserQuestion`; send up to the tool's declared per-call limit.
- **Codex:** use `request_user_input` only when it is listed in the available tools. It may be mode-gated, commonly to Plan mode unless configured otherwise, so absence is expected. Send within the tool's declared per-call limit; batching load-bearing questions is intentional even when the harness prefers fewer questions by default.
- **Fallback:** if no interactive question tool is exposed but the user can reply in chat, ask up to 4 load-bearing questions in concise plain prose. Do not claim to have used an unavailable tool.

Before asking, inspect ambient context: the user's brief, earlier turns, `AGENTS.md` or `CLAUDE.md`, open files, git status, and relevant diffs. Do not ask anything already answered there.

Pick questions whose answers would most change the implementation. Skip anything you can predict with high confidence.

- Bad: "Should I use React?" when the repo already establishes React.
- Good: "Should this live in the existing settings route or as a new top-level page?" when the answer changes file layout and navigation.

Prefer multiple choice when there are clear discrete options. Use `multiSelect` for choose-all-that-apply questions when the tool supports it. For `AskUserQuestion` and Codex `request_user_input`, rely on the tool's automatic free-form `Other` option; do not add your own `Other` choice. For plain-prose fallback, include choices inline and allow a short free-form answer. Use pure open-ended prose only when the answer cannot be framed as a short choice.

Plain-prose fallback format:

```text
The interactive question tool isn't available in this mode, so here is the load-bearing question:

1. Predicting: backfill existing rows in place.
   Should the migration (A) backfill existing rows in place, or (B) leave them null and only populate going forward?
```

### 3. Predict visibly before you ask

For each question, include a short prediction in the visible message before or with the question. Do not rely on hidden reasoning to preserve the calibration loop across models, tools, or context compaction.

Treat the interview as an information game: surprises reveal where your model of the user is off and tell you where the next round should dig. A high hit rate in one area means that area is mapped, not that the whole task is aligned.

During long interviews, periodically restate confirmed decisions in plain text so the accumulated state survives compaction and the user can correct drift.

### 4. Infer tradeoffs as you go

Build a mental model of the user's implicit tradeoff posture from their answers. Common axes: simplicity vs flexibility, short-term vs long-term, prototype vs production-hardened, vendor lock-in tolerance, performance vs readability, build vs buy.

Do not ask explicit "do you prefer X or Y" tradeoff questions. Infer the posture from concrete answers, and restate inferred tradeoffs only when surfacing one would let the user correct a wrong inference.

### 5. Continue until aligned

Default to another round. The threshold is alignment, not count.

Stop only when both are true:

- **Alignment** - you can confidently predict the user's answers to questions that would actually change the code.
- **Diminishing returns** - a plausible next question would not meaningfully change the implementation.

Do not stop because you have asked a lot, the last round had a high hit rate, the user seems eager, or you think sensible defaults might cover the rest.

A direct instruction to proceed always wins. If the user says to stop asking, use your judgment, or just start, stop the interview and proceed with stated assumptions.

**Escape valve:** only when the user seems unsure. If their answers are contradictory, hesitant, or clearly exploratory, surface that: "It sounds like the shape isn't settled yet - want to think on it, or should I propose an approach for you to react to?"

### 6. Confirm and proceed

When you stop, summarize in 1-3 sentences what you are aligned on, including inferred tradeoffs the user should be able to correct.

In plan mode, fold that summary into the plan and use the harness's plan-exit mechanism, such as `ExitPlanMode`, as the proceed gate; do not ask a separate "Ready to proceed?" question. Outside plan mode, ask "Ready to proceed?" unless the user has already directly instructed you to proceed.

## Constraints

- Do not write code or modify project files during the interview.
- Do not ask questions whose answers are already in ambient context.
- Do not dump pre-written assumptions as questions. A question is something whose answer could change the implementation.
- Do not ask explicit tradeoff questions; infer tradeoff posture from concrete answers.
