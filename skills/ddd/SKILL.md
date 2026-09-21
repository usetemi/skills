---
name: ddd
description: >-
  Design, implement, review, or refactor domain models through collaboration
  with the user as the domain expert. Use for domain-driven design, domain
  modeling, ubiquitous language, entities, value objects, domain services,
  aggregates, factories, repositories, domain events, or code whose business
  concepts and rules need to be made explicit. Inspect existing systems before
  interviewing, propose a model for confirmation, then implement only after the
  user approves it. Remain language- and programming-paradigm agnostic.
---

# Domain-Driven Design

Build software around a shared, explicit model of the domain. Treat the user as
the domain expert: extract rules through concrete scenarios, reflect them in a
proposed model, and require confirmation before implementation or refactoring.

Read [`references/domain-driven-design.md`](references/domain-driven-design.md)
before modeling. Use it as the source of truth for concepts and review criteria.

## Operating Contract

- Never invent domain rules. Ask the user when behavior, terminology,
  invariants, or exceptions are unclear.
- Allow an assumption only when the user explicitly approves it. Record approved
  assumptions in the model proposal and preserve them through implementation.
- Do not edit implementation files until the user confirms the proposed model.
- Prefer entities, value objects, domain services, aggregates, factories,
  repositories, and domain events when they clarify the model. Do not force a
  pattern without a concrete domain responsibility.
- Do not require classes, inheritance, mutable objects, or object-oriented
  programming. Express the model using mechanisms natural to the project.
- Do not introduce or recommend bounded contexts. Keep this skill focused on
  domain knowledge, explicit models, consistency boundaries, and evolution.
- Keep the ubiquitous language consistent across conversation, implementation,
  tests, interfaces, and durable documentation.

## Workflow

### 1. Establish The Evidence

For an existing system, inspect the relevant code, tests, schemas, interfaces,
documentation, and recent changes before interviewing the user. Identify:

- current domain terms and competing synonyms
- behavior and rules embedded in conditionals or orchestration
- identities, values, state transitions, and consistency boundaries
- duplicated or scattered domain logic
- persistence concerns leaking into domain behavior
- differences between documentation, tests, and implementation

For a new system, begin with the user's stated problem, actors, desired outcomes,
and representative scenarios. Do not design from nouns or storage structures
alone.

Do not stop after announcing that inspection or an interview is needed. Inspect
available artifacts in the current turn. If no relevant artifacts are available,
start the domain interview immediately.

### 2. Interview The Domain Expert

Use the available interactive question tool. If none is available, ask concise
questions in prose. Ask no more than three or four questions per round and run
additional rounds until material ambiguity is resolved.

Ground questions in concrete cases:

1. Ask what happens in a representative scenario from beginning to end.
2. Clarify the terms the user uses for actors, concepts, actions, and outcomes.
3. Ask what must always be true before and after meaningful operations.
4. Probe exceptions, rejected actions, state transitions, and competing cases.
5. Test the emerging model with counterexamples and boundary cases.

Do not ask the user to choose technical patterns. Ask domain questions, then map
the answers to modeling tools. When an answer exposes a contradiction or a term
with multiple meanings, continue the interview instead of resolving it silently.

### 3. Propose The Model

Present a concise model for confirmation before editing code. Include only
sections relevant to the task:

```markdown
## Ubiquitous language
- **Term**: precise domain meaning

## Model
- **Entity**: identity, lifecycle, behavior
- **Value object**: meaning, attributes, constraints
- **Domain service**: operation and why it belongs outside one concept
- **Aggregate**: root, boundary, invariants, consistency requirements
- **Factory**: creation rules that require encapsulation
- **Repository**: domain-oriented retrieval and persistence needs
- **Domain event**: meaningful occurrence, payload, consumers

## Rules and invariants
- Rule expressed in domain language

## Existing-system mapping
- Current construct -> proposed concept or change

## Approved assumptions
- Assumption explicitly approved by the user
```

Explain why each selected pattern fits. Omit unused patterns instead of filling
the proposal with placeholders. Lean strongly toward explicit modeling tools
when business meaning would otherwise remain in primitives, flags, generic
services, infrastructure code, or unwritten convention.

Ask the user to confirm or correct the proposal. Do not proceed on silence or
partial agreement when unresolved points would change behavior or boundaries.

### 4. Implement Or Refactor

After confirmation, map the approved model onto the project's existing language,
architecture, and conventions.

- Make domain terms visible in names and public operations.
- Keep invariants close to the operations and boundaries that enforce them.
- Represent meaningful values explicitly rather than passing unrelated
  primitives when the language permits a clearer representation.
- Keep domain behavior separate from transport, storage, framework, and UI
  concerns without imposing a new architectural style unnecessarily.
- Use repositories only for domain-oriented persistence access.
- Capture domain events as past-tense facts when occurrences matter to other
  behavior; do not equate domain events with event sourcing.
- Update tests to express scenarios, outcomes, rejected operations, and
  invariants in the ubiquitous language.
- Remove superseded terminology and implementations rather than retaining
  compatibility paths unless requested.

For refactoring, preserve externally required behavior while changing the model
in small, verifiable steps. If the existing behavior contradicts the confirmed
domain model, stop and ask which behavior is authoritative before changing it.

### 5. Validate With The Expert

Run the project's relevant tests and static checks. Then validate the result
against the confirmed scenarios:

- Does the implementation use the approved ubiquitous language?
- Are the rules and invariants explicit and enforced at the right boundary?
- Do tests cover normal cases, rejected actions, transitions, and exceptions?
- Did persistence or framework details distort the model?
- Did any approved assumption change during implementation?

Summarize the implemented model and any remaining assumptions. Ask the user to
validate material domain behavior that automated checks cannot establish.

## Review Output

For review-only requests, remain read-only unless the user later asks for fixes.
Lead with findings ordered by behavioral risk and cite concrete files and lines.
For each finding, state:

- the observed implementation
- the domain concept or rule that is implicit, duplicated, or contradicted
- the consequence for behavior or model evolution
- the smallest modeling change that would make it explicit
- any domain question the user must answer before a fix

Do not report the absence of a tactical pattern by itself. Report a problem only
when the current model obscures domain meaning, permits invalid behavior, leaks
infrastructure, or makes change unnecessarily risky.

## Continuous Refinement

Treat the confirmed model as current, not final. When business behavior evolves:

1. Re-interview the user with concrete changed scenarios.
2. Update the ubiquitous language and model proposal.
3. Confirm the revision.
4. Refactor implementation and tests together.
5. Remove concepts and terms that no longer belong to the model.

Model evolution is expected. Do not protect an obsolete model merely because it
matches the current implementation.
