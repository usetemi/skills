---
name: ask-clarifying-questions
description: Conduct a clarification interview before writing code, using AskUserQuestion in Claude Code, request_user_input in Codex when available, or plain prose questions when the interactive tool is unavailable. Use when the user invokes /ask-clarifying-questions, names ask-clarifying-questions, or asks to build / design / refactor something with a brief vague enough that meaningfully different implementations would all "satisfy" it. The interview output is shared understanding in the current session — no file artifact.
---

# Ask Clarifying Questions

Drive a structured interview to surface load-bearing assumptions before any code is written. Use the agent's interactive question tool when available. The "output" is shared understanding in the current session — no file artifact is produced.

## When to Use

- The user invokes `/ask-clarifying-questions` explicitly.
- The user names `ask-clarifying-questions` in a Codex session.
- The user asks to build a feature, refactor, or design something and the brief is short or leaves room for meaningfully different implementations.
- Skip when: the request is mechanical (typo fix, obvious rename, a one-line bug fix the user has already diagnosed). Cheap requests don't earn an interview — clarification has its own cost.

## Process

### 1. Anchor

Restate in one sentence what you understand the user wants. This anchors the interview and gives the user a chance to redirect cheaply.

### 2. Ask up to 4 questions per round, ranked by load-bearing-ness

Use the interactive question tool for the current agent:

- **Claude Code:** use `AskUserQuestion`. Send up to 4 questions in a single call.
- **Codex:** use `request_user_input` when it is available. Send up to 3 questions in a single call, because that is the tool limit.
- **Codex fallback:** if `request_user_input` is unavailable but the user can still reply in chat, ask up to 4 load-bearing questions in concise plain prose. Say the tool is unavailable, then list the questions directly.
- **Other fallback:** if the current agent does not expose an interactive question tool, ask up to 4 questions in concise plain prose. Do not claim to have used an unavailable tool.

Pick the questions whose answers would most change the implementation — those whose two plausible answers lead to the most different code. Skip anything you can predict with high confidence.

Multiple-choice when there are clear discrete options. Make questions easy to answer with "yes" / "no" or by choosing labeled options like `(A)`, `(B)`, `(C)`. For Codex `request_user_input`, provide 2-3 mutually exclusive choices and rely on the tool's free-form "Other" option when needed. For plain-prose fallback, include the choices inline and allow a short free-form answer when the listed options miss the user's intent. For open-ended cases, give a single best-guess option plus a reasonable alternative when the tool requires choices. Fall back to pure open-ended prose only when the answer truly cannot be framed as a short choice (e.g., the user needs to paste a code snippet or write a paragraph).

Codex plain-prose fallback format:

```text
The interactive question tool isn't available in this mode, so here are the load-bearing questions:

1. Should the new endpoint (A) live under /api/v2 alongside v1, or (B) replace v1 with a deprecation window?
2. Should the migration (A) backfill existing rows in place, or (B) leave them null and only populate going forward?
3. Should the rate limit be (A) per-user, or (B) per-IP?
```

### 3. Predict before you ask

For each question in the batch, write your predicted answer in your reasoning before sending. Treat the interview as an **information game**: surprises (wrong predictions) reveal where your model of the user is off and tell you where the next round should dig. A high hit rate in one area doesn't mean you're aligned overall — it just means you've mapped that area. Use the calibration signal to *guide* the next round, not to decide whether to stop.

### 4. Infer the user's tradeoffs as you go (do not ask)

Build a mental model of the user's implicit tradeoff posture from their answers. Common axes: simplicity vs flexibility, short-term vs long-term, prototype vs production-hardened, vendor lock-in tolerance, performance vs readability, build vs buy. Adjust subsequent rounds to match what you've inferred.

Do **not** ask explicit "do you prefer X or Y" tradeoff questions. Infer it. Restate inferred tradeoffs only when surfacing one would let the user correct a wrong inference.

### 5. After each round, decide: another round or stop?

**Default to running another round.** The threshold is alignment, not a count. You almost certainly aren't there yet, and one more round is cheap compared to building the wrong thing.

The bar for "aligned" is high: you should be able to predict not just what the user wants in broad strokes, but the specific implementation choices they'd make — file layout, error-handling style, what's in scope vs out, how edge cases resolve, which tradeoffs they'd accept. If you couldn't sketch the diff in your head and have the user nod along, you aren't done.

Stop only when **both** are true:

- **Alignment** — you can confidently predict the user's answers to the questions that would actually change the code.
- **Diminishing returns** — a plausible next question wouldn't meaningfully change the implementation.

Things that are **not** reasons to stop:

- "I've already asked a lot of questions." Irrelevant. Count isn't the threshold.
- "My last round had a high hit rate." That tells you you've mapped one area, not that the rest is mapped.
- "The user seems eager to start." They invoked the skill — they want to be aligned, not rushed.
- "I think I can figure the rest out from context." This is the failure mode. Ask.

**Escape valve** — only when the *user* seems unsure (not when you're tired of asking). If their answers are contradictory, hesitant, or they're clearly working it out as they go, surface it: "It sounds like the shape isn't settled yet — want to think on it, or should I propose an approach for you to react to?" Don't use this as an out for your own fatigue.

### 6. Confirm and proceed

When you stop, summarize in 1–3 sentences what you're now aligned on, including any inferred tradeoffs the user should be able to correct (e.g., "Treating this as a prototype — prioritizing simplicity over flexibility"). Ask "Ready to proceed?" — then continue with whatever the next step is.

## Constraints

- **Don't write code or modify project files during the interview.** The interview is read-only and conversational.
- **Use the agent's interactive question tool when available.** Claude Code uses `AskUserQuestion`; Codex uses `request_user_input` when exposed. Plain prose is the fallback when the tool is unavailable or the answer cannot be framed as a short choice.
- **Respect tool limits.** Claude Code: up to 4 questions per round. Codex with `request_user_input`: up to 3 questions per round. Codex without `request_user_input`: up to 4 plain-prose questions per round.
- **No round cap. Default to another round.** Stop on alignment + diminishing returns, never on count. Asking "a lot" is not a reason to bail.
- **Hit-rate is a calibration signal, not a stopping gate.** Use it to steer the next round; don't use it as permission to stop.
- **Escape valve only for genuine user ambiguity** — if the user themselves seems unsure, surface it. Never escape because you're tired of asking.
- **Don't ask questions whose answers are already in the user's brief.**
- **Don't dump pre-written assumptions as questions.** A question is something whose answer could change the implementation.
- **Don't ask explicit tradeoff questions.** Infer the user's tradeoff posture from their answers.
