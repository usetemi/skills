---
name: observability
description: >-
  Opinionated judgment for instrumentation, logging, tracing, alerting, and
  production feedback. Use when deciding what telemetry to capture, designing
  a log record or event vocabulary, choosing operation boundaries, evaluating
  sampling and aggregation, designing alerts or service objectives, choosing
  or adding a telemetry tool, investigating a production outcome, or when a
  change adds or alters an operation whose outcome matters in production,
  even if nobody asked for telemetry.
---

# Observability

**The goal is explainability. The evidence needed to explain a production
outcome exists, and a fresh investigator can find it.** The investigator did
not write the code. Without the author's memory and without reading the
source, they must establish three things: what happened, whom it affected,
and what separated the failed work from the work that succeeded.

The rules below are lessons, not textbook definitions. Load
`references/vocabulary.md` when you define an SLI or SLO, or when you choose
between metrics, records, and traces.

## Every record is structured

Use the project's existing logger. Do not add a second one. If the project
has none, use the language's standard structured logger, writing JSON to
stdout or stderr.

Never write an unstructured log line. A sentence with values interpolated
into it throws away data the program already held. It throws the data away
at the moment it was cheapest to keep. Emit one structured record per event.
The record has a stable event name, a small set of typed fields, a
timestamp, and a severity. The event name is a literal that the code
declares. Never assemble it at runtime. The investigator will grep for it.

Keep each field's meaning, type, and unit fixed across the codebase.
`duration_ms` is milliseconds everywhere. The `result` field takes its values
from one list everywhere: `succeeded`, `failed`, `skipped`, `retried`,
`degraded`, `unknown`. If two records spell the same fact two different ways,
they cannot be compared. Most of an investigation is comparison.

A **reason code** is a value from a closed list that the code declares in one
place, such as `payment.failure.reason_code: card_declined`. Use reason codes
instead of free-text explanations, so causes can be counted.

Use scoped field names, such as `payment.result` and
`payment.failure.reason_code`. They cost nothing. They make a record
self-describing when it is read out of context, and records are always read
out of context.

## Preserve the operation

Instrument at the boundary of a meaningful unit of work. That unit is a
request, a job, or a business operation with a durable effect. Its outcome,
its duration, and its relevant context belong together in one record or one
span. Scattered progress messages make the investigator rebuild what the
program already knew.

A **terminal record** is the last record an operation writes before it
exits. It carries the operation's outcome, duration, and reason code.
**Write one terminal record on every exit path, including a throw.** The
terminal record is the operation's contract with the investigator. Some
operations record success but return silently on failure. Others record
failure but forget the early return. Either way, the hole is exactly where
the question will be asked.

**Unknown is its own outcome.** Sometimes an operation starts a side effect
and never learns whether it landed. A transmit call times out. A webhook is
acknowledged before the write. Record that outcome with the result `unknown`.
Do not record it as success or as failure. An unknown outcome cannot claim
"it did not happen." That false claim is what causes a duplicate side
effect. Before you retry, check the downstream system's state.

Instrument the owner of the durable operation, not every wrapper it passes
through. Write one record per attempt, with its attempt number, plus one
terminal record for the whole operation. Long-running work emits a progress
record at a fixed interval, so a slow run and a dead run look different.

Automatic instrumentation captures technical activity: an HTTP request, a
query, a fetch. Add what it cannot infer: the decision taken, the relevant
state, and the outcome the caller received. Carry causal identifiers across
service calls, queues, retries, and background work. The main one is the
**operation id**: the request id or job id that identifies one operation.
Pass these identifiers through the project's existing context-propagation
mechanism (request headers, message fields, or async context). Do not invent
a new one. Nearby timestamps do not prove that two events belong to the same
operation.

## Make the evidence countable

Explanation usually starts as a count: how many, how often, and by what
cause. Design records so that each count is a filter plus a group-by. It
should never require parsing.

- **Counts check themselves.** A batch record reports the total and the count
  for each outcome, and the counts sum to the total. Then a total of zero
  means the work really was idle, and counts that do not add up are a bug.
- **Log every run.** A scheduled sweep writes a record on every run,
  including runs that found nothing. Otherwise a sweep that found nothing
  looks the same as a sweep that stopped running. Zeros are data.
- **Ask the question before you choose the fields.** Take the question "How
  many sends fell back to fax last week, by cause?" It names the event, the
  filter, and the group-by. Write the record to answer it. A record that
  cannot answer a named question is decoration.

## Severity is an alert decision

`error` means a person must spend attention now. If a failure does not
deserve that, it is `warn`. If it does, it is `error`, and it alerts. A
recovered failure is `warn`. An expected business rejection is `warn`. Only
three things are `error`: an unexpected terminal failure, exhausted recovery,
and a broken invariant.

**Every uncaught exception must reach an alert.** A catch block either
rethrows or writes the terminal record. A catch that logs and continues
without one hides the failure, and that is a defect. Check whether the
project already routes unhandled errors to an alert, through a
process-level handler, a framework error boundary, or an error tracker. If
it does not, add that path in the same change. The path emits an `error`
record.

Group errors by event name, not by stack trace. Count and alert per event
name. A shared wrapper's stack trace mixes unrelated failures, and one
event's different stack traces are one problem. An alert is actionable when
it names an owner, a starting point, and the count so far. Repeated alerts
that need no action are worse than no alert. They teach people to stop
reading.

## Alerts come from the event

A Slack post, an alert, and a log record for the same event all come from
one emit call for that event. Do not scatter separate post-message calls
through business code. When the event changes, every output changes with
it. When an output is missing, the list of events shows the gap.

## Choose tools by the question

**Metrics count. Events explain.** Use aggregates for population questions:
rate, share, percentile. Keep event-level records for the outlier. A metric
can say that requests got slow. Only the record can say which request, for
whom, and what was different about it. Never put unbounded values, such as
ids or URLs, into metric labels. Put them in the record.

**The terminal record is the primary evidence. A trace is secondary.** A
trace shows where time went inside one operation as it crossed boundaries.
It does not carry the decision or the outcome. The terminal record does. Put
the trace id on the record, and reach the trace from there.

**Correlation is a contract, not a coincidence.** Sending everything to one
backend does not connect the records. Propagate the operation id, the trace
id, and the session or actor id on purpose. Treat a record that arrives
without them as a defect.

## The pipeline is code too

This section applies when the project owns a telemetry pipeline: a shipper,
a collector, or a transform between the app and the store. The telemetry
pipeline is code, and it fails like code. When the pipeline drops a record,
it writes a payload-free record that says so and why. When the pipeline has
to prune fields from a record, it records how many it pruned. When a
heartbeat record that should arrive on a schedule stops arriving, the
absence is an alert. It is not something a person notices later. A transform
that errors must drop the record, so an unredacted payload cannot leak
downstream. The drop is not silent, because the pipeline records every drop
as above.

## Measure what was promised

Healthy components and successful protocol responses can coexist with a
failed user journey. Define the objective around the outcome the user was
promised. For example: the message was delivered, or the order reached the
supplier. The indicator (the SLI) is derived from the terminal records that
report that outcome. The target for it is the SLO. HTTP status, CPU, and
queue depth are diagnostic inputs. They are not the promise. For error
budgets, burn rate, and the aggregation rules, load
`references/vocabulary.md`.

State the measurement boundary in the objective: where it is measured, which
requests are eligible, and how a timeout counts. An objective measured
inside the handler misses the requests that never reached it.

## Bound the cost

Collect context on purpose. Record opaque identifiers and reason codes. Do
not record the personal, clinical, or secret content behind them. When a
value is forbidden, leave it out. Truncating it, hashing it, or redacting it
inline still records it. A scrubber downstream is a backstop, not the rule.

Cap the record size at the source. When a record is too large, prune it in a
fixed, deterministic order. That order protects the fields an investigation
needs most: the event name, the result, the reason code, and the ids.

## Close the feedback loop

Add instrumentation in the same change that introduces the behavior. During
implementation, decide what evidence would separate the intended result from
a failure or an unexpected outcome. Ship that evidence in the same release.
Write a test for each exit path that asserts exactly one terminal record is
written. After release, run the question the record was designed to answer
against production, and confirm at least one record came back as expected.
If you cannot query production, say so in the PR instead of claiming the
check. A new operation without its terminal record is incomplete. It is not
shippable.

Sometimes an investigation needs instrumentation that does not exist. That
is feedback on the design. Fix it in the code. Do not answer it with a
longer investigation.

## Investigate from the evidence

Investigate from evidence, and stop where the evidence stops. Start from the
narrowest source that could hold the answer. Grep the literal event name,
then its result. If the evidence is not there, say so. Inferring the missing
record is how a wrong root cause gets written down.
