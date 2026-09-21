# Domain-Driven Design Reference

Domain-driven design aligns software with the domain it serves. Its central practice is to build a shared model with domain experts, express that model directly in the software, and refine both as understanding and business needs evolve.

Use domain-driven design where the domain is complex enough that misunderstanding business concepts, rules, or relationships presents material risk. Do not force it onto simple technical or data-processing problems that do not contain meaningful domain behavior.

## Collaborate With Domain Experts

Software specialists cannot derive a reliable domain model from requirements documents alone. Domain experts understand the work, terminology, rules, exceptions, and business consequences. Software specialists know how to organize that knowledge into an implementable model. Neither group can produce the model independently.

Interview domain experts using concrete scenarios:

- Ask what happens in a representative case from beginning to end.
- Identify the people, concepts, decisions, rules, and outcomes involved.
- Ask what can change, what must always remain true, and what exceptional cases occur.
- Challenge vague or overloaded terms with specific examples.
- Test tentative models against real and counterexample scenarios.
- Revisit disagreements; they often reveal missing or conflated concepts.

Treat communication as a feedback loop, not a one-way transfer of requirements. Software specialists extract and organize domain knowledge, then express it as terminology, behavior, constraints, and prototypes. Domain experts evaluate that expression and correct misunderstandings. Implementation exposes gaps and contradictions, which feed back into the model.

Software specialists and domain experts create the model together. The model is where domain knowledge and implementation knowledge meet. This takes time, but software intended to solve business problems must fit the domain.

Prefer conversations and concrete examples over large, static documents. Record durable decisions and definitions, but keep documentation synchronized with the language, model, and implementation.

## Build a Ubiquitous Language

A ubiquitous language is the shared language used by domain experts and software specialists to discuss the domain. Use it consistently in conversation, requirements, tests, documentation, interfaces, data structures, and implementation.

The language is part of the model, not a glossary layered over it. Its terms should express important domain concepts and relationships precisely enough that domain experts recognize them and software specialists can implement them.

To develop the language:

1. Start with the terms domain experts use in concrete scenarios.
2. Define each important term through examples and behavior, not only synonyms.
3. Identify synonyms that refer to the same concept and choose one term.
4. Identify overloaded terms that hide distinct concepts and give each a precise name.
5. Use verbs to expose domain operations, decisions, and state transitions.
6. Use the language in the model and implementation immediately.
7. Refine names whenever the current language causes confusion or fails to express new insight.

Do not translate continuously between business vocabulary and implementation vocabulary. That translation creates ambiguity and knowledge loss. If a concept matters in the domain, represent and name it explicitly in the software.

Read implementation terminology as a model review. Names that are generic, technical, or inconsistent with domain speech may indicate a weak or missing domain concept. Terms such as `manager`, `handler`, `processor`, `data`, or `status` deserve scrutiny when a more precise domain term exists.

## Practice Model-Driven Design

A domain model is a selective abstraction of domain knowledge. It is not a diagram, schema, class hierarchy, or data structure, though any of those may express part of it. The model captures the concepts, behavior, relationships, and rules needed to solve the problem.

Keep the model and implementation aligned:

- Choose a model that can be expressed naturally in the implementation.
- Make important domain concepts visible in names, boundaries, behavior, and tests.
- Treat implementation feedback as evidence about the model.
- Recognize that a significant implementation change may also be a model change.
- Involve implementers in modeling and domain conversations.
- Avoid a separate analysis model that drifts away from the implemented model.

Domain-driven design is independent of programming paradigm. Express the model using the language and architectural mechanisms appropriate to the system. Entities, value objects, services, aggregates, factories, and repositories describe modeling responsibilities and boundaries; they do not require classes, inheritance, mutable objects, or object-oriented programming.

### Entities

An entity is defined by continuity and identity rather than by its current attributes. Its attributes and representation may change while it remains the same domain concept.

Use an entity when the domain must distinguish one instance from another across time or state changes. Define:

- What establishes its identity.
- Whether that identity is unique globally or within a narrower scope.
- Which behaviors and state transitions belong to it.
- Which invariants it must preserve.

Do not give every record an identity merely because it has a database key. Technical identifiers do not automatically make a concept a domain entity.

### Value Objects

A value object describes a domain value through its attributes and meaning. Two value objects with the same meaningful attributes are interchangeable.

Use value objects to make measurements, quantities, ranges, dates, addresses, money, identifiers, and other descriptive concepts explicit. Prefer value objects over unrelated primitive values when the concept has domain meaning, validation, units, or behavior.

Value objects should form conceptual wholes. Keep their constraints close to their construction and operations so invalid values are difficult to represent. Immutability is often useful but is an implementation choice, not the definition.

### Domain Services

A domain service represents domain behavior that does not naturally belong to one entity or value object. It often coordinates several domain concepts or performs a domain operation whose result matters independently of a particular entity.

Use a domain service when:

- The operation is expressed in the ubiquitous language.
- Assigning it to one participating concept would distort that concept.
- The behavior contains domain rules rather than infrastructure or application orchestration.

Name services after the domain operation they perform. Keep them focused and stateless where practical. Do not move behavior into services merely to leave entities as passive data containers.

### Aggregates

An aggregate is a consistency boundary around domain concepts that must change together. It has a root through which external interactions occur. The root protects invariants for the aggregate as a whole.

Design aggregates around transactional consistency and domain rules, not object graphs or convenient data loading. Within an aggregate:

- Enforce invariants at the boundary.
- Perform changes through the root's public domain operations.
- Avoid external dependencies on internal representation.
- Commit a state change as one consistent operation.

Keep aggregates as small as the invariants allow. Concepts that do not require immediate consistency can coordinate through identifiers, explicit operations, or domain events rather than belonging to one aggregate.

### Factories

A factory encapsulates creation when constructing a valid domain concept requires meaningful rules, coordinated values, or multiple steps. It should produce a complete, valid result or fail without exposing a partially constructed one.

Use a factory when creation logic would otherwise:

- Expose internal representation.
- Be duplicated across callers.
- Require knowledge that does not belong to the caller.
- Obscure the domain operation being performed.

Simple construction does not need a factory. Introduce one only when creation itself carries domain complexity.

### Repositories

A repository provides access to persisted aggregate roots using domain-oriented language. It separates the domain model from storage queries and reconstruction details.

Define repository operations from domain use cases, not from every query the storage technology can perform. A repository may retrieve an aggregate by identity, find aggregates meeting a domain criterion, and persist changes while preserving the aggregate boundary.

Do not expose storage records or persistence mechanics through repository interfaces. Reporting, search, and bulk analytics may use separate read-oriented mechanisms when reconstructing domain aggregates would add no value.

### Domain Events

A domain event records a meaningful occurrence in the domain. Name it as a past-tense fact using the ubiquitous language, and include the domain information needed to understand what happened.

Use a domain event when an occurrence matters beyond the operation that produced it, such as when it triggers another domain behavior, informs another part of the system, or must be represented explicitly in the model. Do not create events for incidental implementation steps or generic data changes.

Domain events do not require event sourcing, asynchronous messaging, or object-oriented programming. They may be represented and handled using mechanisms appropriate to the system. Keep the event's domain meaning separate from transport envelopes, delivery retries, and integration-specific payloads.

## Bring Key Concepts Into Light

Deep modeling often begins with important ideas hidden in procedures, conditionals, loosely related fields, or overloaded terminology. Make those concepts explicit.

Look for hidden concepts in:

- Repeated conditional logic that represents the same business distinction.
- Rules distributed across several modules or services.
- Primitive values that carry units, validity rules, or domain meaning.
- Generic names used where domain experts use a precise term.
- State represented by combinations of flags with implicit valid transitions.
- Important processes described in conversation but absent from the model.
- Exceptions and edge cases that reveal a missing classification or policy.

When a hidden concept emerges, name it in the ubiquitous language and give it an explicit representation with clear behavior and constraints. Update conversations, tests, documentation, and implementation together.

Do not preserve an awkward model merely because the implementation already reflects it. New domain insight justifies changing structure and boundaries when the result is a clearer, more faithful model.

## Refactor Continuously

A domain model is never complete. Understanding deepens through interviews, implementation, production behavior, policy changes, and new business needs. Treat the model as a living part of the system.

Continuous refactoring is a modeling practice, not only code cleanup:

1. Observe new domain knowledge or recurring confusion.
2. Identify the concept, distinction, rule, or relationship the current model misses.
3. Update the ubiquitous language.
4. Change the model and implementation together.
5. Update tests to express the refined behavior and invariants.
6. Validate the result with domain experts using concrete scenarios.

Refactor in small steps and maintain working behavior. Automated tests make it possible to change the model without losing established rules. Tests should express domain outcomes and invariants, not merely mirror implementation structure.

Watch for model drift during maintenance. A local patch that introduces a synonym, bypasses an aggregate invariant, duplicates a rule, or adds a generic flag may solve the immediate problem while weakening the model. Prefer a change that incorporates the new requirement into the model explicitly.

## Review an Existing System

Review the system against the domain rather than checking only its internal code organization.

### Language

- Do domain experts and software specialists use the same terms?
- Are important terms precise, consistent, and visible in the implementation?
- Do generic or technical names conceal domain concepts?
- Are the same words used for different concepts, or different words for the same concept?

### Model

- Which concepts have stable identity and should be entities?
- Which concepts are values defined by their attributes?
- Where does domain behavior live, and is it assigned coherently?
- Which rules must hold across a group of changes?
- Are aggregate boundaries based on those invariants?
- Does complex creation preserve validity atomically?
- Do repositories express domain needs without leaking persistence details?

### Explicitness

- Which rules are duplicated or scattered?
- Which state transitions are implicit in flags or conditionals?
- Which primitives carry unmodeled domain meaning?
- Which business processes exist only in developers' or domain experts' heads?

### Evolution

- Does the implementation still match the current business language and rules?
- Are model changes validated with domain experts?
- Do tests protect domain behavior and invariants during refactoring?
- Are new requirements extending the model or accumulating as exceptions around it?

Use the answers to identify the smallest model changes that make domain knowledge more explicit. Refactor terminology, behavior, boundaries, and tests together rather than applying isolated structural patterns.
