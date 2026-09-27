---
name: observability
description: >-
  Design judgment for instrumentation and production feedback. Use when
  deciding what telemetry to capture, choosing operation boundaries,
  evaluating sampling and aggregation, designing alerts, determining how to
  verify a change in production, or when a change adds or alters an operation
  whose outcome matters in production, even if nobody asked for telemetry.
---

# Observability

**Explainability: the evidence needed to explain a production outcome is
available.** Judge telemetry by the questions it makes answerable.

Design for a fresh investigator. Can someone who did not write the code
establish what happened, whom it affected, and what distinguished affected
work from successful work? The explanation should survive in the evidence,
without depending on the author's memory. When a change introduces an
operation with a production outcome, ship the evidence that explains that
outcome in the same change, through the project's existing telemetry path.

## Preserve the operation

A meaningful unit of work—a request, job, or business operation—is the
natural boundary for instrumentation. Keep its outcome, duration, and
relevant context together in a structured event or span. Scattered log
messages force the investigator to reconstruct information the program
already held.

Instrument where the outcome is known. Distinguish an attempt from the
operation it serves: a failed attempt followed by successful recovery is
different from an operation that exhausted its retries. Long-running work
also needs progress evidence.

Automatic instrumentation captures technical activity. Add the application
meaning it cannot infer: the decision taken, the relevant state, and the
outcome the caller received. Carry causal relationships across service calls,
queues, and retries. Nearby timestamps do not establish that two events
belong to the same operation.

## Preserve exploratory power

Investigations ask questions nobody anticipated when the code was written.
Keep enough detail to filter, compare, and inspect individual events.

Identifiers and contextual attributes often explain what makes an outlier
different. Preserve useful distinctions in events and spans; avoid unbounded
metric labels that multiply time series. Keep field meanings, types, and
units consistent so comparisons remain uniform.

Use metrics for population measures and retain event-level evidence for
explanation.

## Close the feedback loop

Instrumentation belongs in the change that introduces the behavior. Decide
during implementation what evidence would distinguish the intended result
from failure or an unexpected outcome. After release, inspect that evidence.

When investigation requires new instrumentation, treat that as feedback on
the design.

## Spend attention on user impact

Measure whether the work users depend on actually succeeds. Healthy
components and successful protocol responses can coexist with a failed
user journey. Define service-level objectives around the outcome being
promised.

An alert spends someone's immediate attention. It should be actionable,
identify an owner, and provide a useful starting point for investigation.
Work that can wait belongs in a less disruptive channel. Repeated alerts
that require no useful action lead to alert fatigue.

## Bound the cost

Collect context deliberately. Record opaque identifiers and bounded reason
codes rather than the personal or secret content behind them; when a value
is forbidden, leave it out, because truncating, hashing, or inline-redacting
it still records it. An opaque identifier is not automatically anonymous.
