# Observability Vocabulary

This file gives precise meanings for the terms the skill uses. The terms
name different kinds of things: data, mechanisms, practices, and promises.

| Term | Kind of thing | Meaning |
| --- | --- | --- |
| **Observability** | Capability | How well a system's internal behavior can be explained from its outputs, including behavior nobody anticipated. It is a property of the system and its evidence. It is not a tool. |
| **Monitoring** | Practice | Watching a system over time through measurements, checks, dashboards, and alerts. Monitoring can detect a problem. It can explain one only as far as the evidence allows. |
| **Telemetry** | Data, umbrella term | Everything emitted or collected about a system's behavior. |
| **Signal** | Category of telemetry | One kind of evidence: metrics, logs, or traces. Spans are not a signal. They are the parts a trace is made of. |
| **Instrumentation** | Mechanism | The code, libraries, agents, or hooks that produce telemetry. Automatic instrumentation captures technical boundaries. Manual instrumentation adds application meaning. |
| **Pipeline** | Mechanism | The path telemetry takes from producer to store: collection, validation, transformation, and export. It has its own failure modes, so it needs its own evidence. |

## The signals

| Signal | Answers | Shape |
| --- | --- | --- |
| **Metric** | How much, how often, and how bad, over time. | A numeric measurement aggregated by dimensions. A counter accumulates. A gauge rises and falls. A histogram records a distribution, and percentiles are derived from it. Aggregation discards the individual case by design. |
| **Log record** (event) | What happened, with what details, at what moment. | A timestamped structured record with an event name, a severity, and attributes. It is the unit of explanation for one operation. |
| **Trace** | What path one operation took across boundaries, and where its time went. | A tree of spans that share a trace id. One span is one timed operation with a name, a start, an end, a status, and attributes. A parent's duration already includes its children. Do not add child durations to it. |

**Metric versus indicator.** A metric is a measurement. A service level
indicator (SLI) is a role that a chosen measurement plays: it judges service
quality. An SLI can be computed from counters, histograms, or log records.

**Sampling versus aggregation.** A histogram folds every observation into a
compact summary. Sampling keeps some observations whole and drops the rest.
A sample biased toward errors or slowness cannot be read as a rate.

## Service quality

| Term | Meaning |
| --- | --- |
| **SLI** | A precisely defined measurement of delivered service. It states the numerator, the denominator, where it is measured, which requests are eligible, and how a timeout counts. |
| **SLO** | A target for an SLI over a window. Example: 99.9% of eligible requests complete within 500 ms over 30 days. |
| **Error budget** | The bad outcomes the SLO permits in the window. It is a count of requests, not a number of minutes. Example: 0.1% of one million eligible requests is 1,000 bad requests. |
| **Burn rate** | How fast the budget is being used up, relative to the SLO. A 1% bad rate against a 0.1% allowance is a 10x burn. An alert on burn rate warns before the window is missed. |

## Identity and correlation

| Term | Meaning |
| --- | --- |
| **Resource attributes** | Metadata about the thing that produced the telemetry: service name, instance id, version, region. They differ from attributes that describe one operation. |
| **Context propagation** | Carrying the trace and operation identity along the execution path. It crosses HTTP (the W3C `traceparent` header), queues, and background jobs. |
| **Correlation** | Connecting evidence through propagated ids, or through shared resource and time metadata. |
| **Cardinality** | The number of distinct values a dimension takes. |

## Aggregation rules

- A service-wide rate is the sum of the numerators divided by the sum of the
  denominators across instances. It is never the mean of per-instance rates.
- A service-wide percentile is computed from the merged distribution. It is
  never the mean of per-instance percentiles. Histograms merge. Percentiles
  do not.
