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
available.** Judge telemetry by the questions it makes answerable and the
decisions it improves.

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
also needs progress evidence; completion records cannot explain work that
never completes.

Automatic instrumentation captures technical activity. Add the application
meaning it cannot infer: the decision taken, the relevant state, and the
outcome the caller received. Carry causal relationships across service calls,
queues, and retries. Nearby timestamps do not establish that two events
belong to the same operation.

## Preserve exploratory power

An investigation's next question depends on its previous answer. Preserve
enough detail to filter, compare, and inspect individual experiences beyond
the questions anticipated when the code was written.

Identifiers and contextual attributes often explain what makes an outlier
different. Preserve useful distinctions in events and spans; avoid unbounded
metric labels that multiply time series. Keep field meanings, types, and
units consistent so comparisons remain trustworthy.

Aggregation is irreversible: a summary cannot recover the individual
experiences it discarded. Use metrics for population measures and retain
event-level evidence for explanation. Dashboards are useful starting points
when investigators can follow their questions into the underlying data.

Evaluate sampling and retention by the questions they make impossible.
Retaining unusual failures helps diagnosis, but a biased sample cannot
establish population rates or latency distributions without accounting for
how it was selected. Missing evidence is not evidence of success.

## Close the feedback loop

Instrumentation belongs in the change that introduces the behavior. Decide
during implementation what evidence would distinguish the intended result
from failure or an unexpected outcome. After release, inspect that evidence.

Tests establish behavior under chosen conditions. Production observation
reveals behavior under actual conditions. The engineers changing a system
need both to understand what they shipped.

When investigation requires new instrumentation, treat that as feedback on
the design. Add the missing context where it originates so future questions
require less reconstruction.

## Spend attention on user impact

Measure whether the work users depend on actually succeeds. Healthy
components and successful protocol responses can coexist with a failed
user journey. Define service-level objectives around the outcome being
promised; use component signals to help explain deviations.

A page spends someone's immediate attention. It should indicate actionable
user harm or credible imminent harm, identify an owner, and provide a useful
starting point for investigation. Work that can wait belongs in a less
disruptive channel. Repeated alerts that require no useful action erode the
value of every subsequent alert.

## Bound the cost

Collect context deliberately. Record opaque identifiers and bounded reason
codes rather than the personal or secret content behind them; when a value
is forbidden, leave it out, because truncating, hashing, or inline-redacting
it still records it. An opaque identifier is not automatically anonymous.

Bound diagnostic overhead so observing an operation does not prevent it
from completing. Diagnostic telemetry may be dropped under pressure;
mandatory audit records have a separate contract and may not. Make dropped
or unavailable telemetry visible so readers can distinguish a quiet system
from a blind one.
