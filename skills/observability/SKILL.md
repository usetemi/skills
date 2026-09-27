---
name: observability
description: >-
  Design judgment for making production behavior explainable from the evidence
  a system emits. Use when deciding what an operation should record and where,
  reviewing instrumentation in a change, designing an alert or page, weighing
  telemetry cost, privacy, sampling, or retention, or investigating production
  behavior from logs, events, metrics, or traces.
---

# Observability

**Make production behavior explainable from the evidence the system emits.**
Observability is the ability to investigate how software actually behaves,
including questions nobody anticipated when writing it. Judge instrumentation
by the understanding it enables, not by its volume.

Design for a fresh investigator: someone who did not write the code and has no
memory of the incident. Can they establish what happened, whom it affected, and
what distinguished affected work from successful work? If ordinary
investigation requires the author's memory or another deployment to add
logging, context is missing at the source.

## Follow the work

Organize evidence around meaningful units of work: a request, a job, a
workflow, a business operation. Choose boundaries where an outcome matters to a
caller. Healthy infrastructure and successful protocol responses do not
establish that the user's work succeeded.

Keep an operation's outcome, duration, and the decisions that shaped it
together in one structured event or span, recorded where the outcome is known.
Repeated messages from every layer make the investigator reconstruct a story
the program already held.

Distinguish attempts from outcomes. A recovered dependency failure, an expected
rejection, and an exhausted retry describe different behavior. Preserve those
distinctions instead of assigning severity wherever an exception happens to be
caught. Long-running work also needs evidence of progress; a completion event
cannot explain an operation that never finishes.

## Preserve context and relationships

Automatic instrumentation exposes technical activity. Application
instrumentation supplies the meaning: what operation was attempted, which
decision path it took, and what outcome the caller received.

Preserve the attributes that distinguish one experience from another and
explain differences between populations. Put correlation identifiers on events or spans; unbounded metric labels multiply
storage and cost.

Carry causal relationships across service calls, queues, retries, and
background work. Record which attempt belongs to which operation and which work
triggered subsequent work. Nearby timestamps suggest a relationship; they do
not establish one.

Use consistent names, types, units, and outcome meanings. A field whose meaning
changes between services creates ambiguity exactly when the reader needs
evidence. Extend context without making existing meanings unreliable.

## Make the next question answerable

Metrics summarize populations; structured events retain individual context;
traces connect work across boundaries. Keeping only aggregates permanently
discards the distinctions needed to explain an outlier.

Dashboards give shared orientation and starting queries. Their value grows when
a reader can move from a summary to the evidence behind it.

## Close the development loop

Instrumentation belongs in the change that introduces the behavior. While
implementing, decide what evidence would show that the change works, fails, or
produces an unexpected result, then inspect that evidence after release.

Tests establish behavior under chosen conditions; production observation
reveals behavior under actual conditions. Both contribute to confidence.

When an incident exposes missing context, improve the instrumentation at its
source so the next investigation needs less private knowledge.

## Spend attention deliberately

A page spends someone's immediate attention. It needs an owner, a
time-sensitive action, and enough context to begin investigating. Page for
actionable user harm or credible imminent harm; route work that can wait
through a less disruptive channel.

Alert on outcomes users depend on. Component health helps explain a failure and
is a poor substitute for measuring the outcome itself.

Repeated alerts that demand no useful action train people to ignore the
system. Change the signal, its routing, or the underlying behavior.

## Make evidence limits explicit

Telemetry costs collection, storage, privacy, and human attention. Spend those
costs on distinctions that improve understanding.

Record opaque identifiers and bounded reason codes, never the personal or
secret content behind them. When a value is forbidden, leave it out and offer
an identifier plus a reason code instead; truncating, hashing, or inline
redaction to get a forbidden value past a check still records it. An opaque
identifier is not automatically anonymous.

Sampling and retention are deliberate choices with stated consequences.
Selectively retained failures cannot establish error rates or latency
distributions without a representative baseline.

Diagnostic telemetry must not prevent the user's work from completing; bound
its overhead and make export failures, dropped records, and sampling visible.
Mandatory audit records have a separate contract and are not diagnostics.

## Investigating

1. Start from an observed symptom and an affected population.
2. Compare affected and unaffected work, narrow the differences, and inspect
   concrete examples. Let each answer decide the next question. Coincident
   graph spikes are a hypothesis to test.
3. Separate what the evidence shows from what you infer, and say which is
   which.
4. Missing evidence is not evidence of success. State what the available data
   establishes and what remains unknown.
