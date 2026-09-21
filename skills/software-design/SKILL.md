---
name: software-design
description: >-
  Design judgment for modules, interfaces, and where information lives. Use
  when designing or restructuring a module or interface, deciding where an
  abstraction goes, evaluating a decomposition, placing rationale in comments
  or scoped docs, or comparing alternative designs for a larger change.
---

# Software Design

**Reduce the amount of information a developer must know, and make the
remaining information obvious.** Software complexity is whatever makes a
system difficult to understand or modify—especially when essential information
is hidden or distant. The goal is **information locality**: the information
needed to understand and modify a part of the system is colocated and easy to
find.

Design for the reader, and the reader is a fresh session: the next engineer, a
reviewer, or an agent with no memory of this conversation. Whatever the author
knew — the request, the rejected alternatives, the failure that shaped the
fix — survives only if it lands in the repository: code, names, comments,
contracts, tests, or the nearest scoped `AGENTS.md`. Judge a design by how
much a fresh reader must gather before they can change it safely.

## Deep modules

A deep module concentrates knowledge: a good abstraction replaces a large
implementation burden with a much smaller interface burden. Callers get
leverage — one implementation pays back across every call site — and
maintainers get locality — change, bugs, and verification concentrate in one
place. When designing an interface, ask: can it have fewer methods, simpler
parameters, more hidden inside?

- **The interface is the test surface.** Callers and tests use the same
  interface. Wanting to test past the interface usually means the module is
  the wrong shape.
- **The fresh-reader test.** Can someone use the module correctly from its
  interface alone, without opening the implementation or its siblings? If
  crucial behavior is discoverable only by reading the implementation, the
  interface is incomplete; state it in the interface's comment.

## Decomposition

More files, functions, layers, or services is not more modularity. Every
split adds a place a reader must find, load, and reconnect — so split only
when the piece can be understood from its interface without loading its
neighbors. When understanding one piece routinely requires reading three
siblings, the split scattered the logic instead of hiding it; recombine or
deepen instead.

Scattering applies to knowledge too: one invariant half-stated in two
documents, a policy duplicated across layers, a rationale narrated in both a
comment and a nearby `AGENTS.md`. Keep one canonical statement at the
narrowest durable place and link to it from everywhere else — two copies
drift.

There is no useful static threshold for size — lines of code must grow with
essential behavior. A long module that reads top to bottom in one place often
beats a short one that forwards to five others. Judge by the information a
reader must hold, not by static analysis.

## Volatility

How much change is coming to a part of the system is usually written down,
not guessed. The gap between the project's declared goal state and the current
implementation, its roadmap and scope decisions, and open issues all declare
where change is planned and where it is not.
Commit history is not a signal: frequent edits can mean a bad design
forcing rework, not a volatile domain.

An awkward design in an area with no declared change ahead is tolerable
debt. The same flaw on a path the roadmap keeps touching taxes every
future change. When nothing declares an area's future, assume ordinary
volatility rather than using stability as an excuse. Spend design effort
where declared change is coming.

## Where information lives

Code states what happens; it cannot state intent, rejected alternatives,
incident history, or which behavior callers may rely on. Put each fact at the
narrowest durable place a reader will actually encounter:

- **A type, schema, constraint, or lint** for anything an agent could
  otherwise silently violate — prose is advisory; mechanisms survive
  imperfect attention.
- **The interface's comment** for the contract: what callers may depend on.
- **An adjacent comment** for local rationale a reader cannot reconstruct
  from the code.
- **The nearest scoped `AGENTS.md`** for subsystem workflow and conventions.

## Comments

**A comment carries information that cannot be expressed in code.** The test
for any comment: does it help the next reader build an adequate theory of the
program? The author is inside the box, writing to a reader who stands outside
and cannot see what the author saw.

A comment that restates *what* the code does fails the test — it adds reading
without adding information, and it goes stale when the code moves. Write what
the code cannot say:

- **On an interface, what a caller would otherwise get wrong.** Picture a
  caller who sees only the signature. What would they assume wrongly? What
  would they have to open the implementation to learn? Say that. Use a name
  or a type first when the language allows, and comment only what is left. If
  the signature says everything, write no comment. A widely used interface
  needs its full contract. A private helper with one nearby caller usually
  needs nothing. Do not repeat what the module's comment already says.
- **In an implementation, why — and whatever is not obvious.** The reason the
  code takes this shape (efficiency, a vendor quirk, an incident), the key
  idea of a non-obvious algorithm, the invariant that must not change
  casually, and where it is verified.
- **Key ideas and conclusions, stated explicitly.** Do not leave the reader
  to deduce what the author already knows.

A comment cannot — and need not — say everything. Comments about purpose and
reasoning stay true longer than comments that name the pieces currently in
place.
