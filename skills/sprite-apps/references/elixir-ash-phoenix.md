# Elixir, Ash, and Phoenix

The stack reference for sprite-apps builds. These are standing conventions,
not suggestions to re-litigate per project.

## Elixir

- **Elixir 1.20**, using its latest built-in type-checking capabilities.
  **Do not add Dialyzer.** Elixir 1.20 ships no standalone type checker; the
  working substitute is a warning-free build with `warnings_as_errors`
  enabled, kept on in every environment that compiles the project.
- **Write elegant, idiomatic Elixir.** If a construct would surprise a
  strong Elixir reader, it is wrong until justified.

## The anti-patterns pass

Before shipping, review the change against the official anti-patterns
catalog: <https://elixir.hexdocs.pm/1.20.4/what-anti-patterns.html>

The catalog has four categories: code-related, design-related,
process-related, and meta-programming anti-patterns. Check all four that
apply to the change, and **cite anti-patterns by their catalog name in
findings**. A name both parties can look up turns a taste argument into a
shared diagnosis.

Matching a catalog entry is a prompt to look, not an automatic rewrite: the
catalog itself says a matching snippet may still be the best approach.
Where a match is kept, record why at the narrowest durable place (per
`software-design`: a comment, the interface contract, or the nearest scoped
`AGENTS.md`).

## Ash

- **Model the domain as Ash resources and actions, end to end.** Features
  are modeled idiomatically in the domain layer (resources, actions,
  calculations, policies) rather than re-implemented in controllers,
  LiveViews, or ad-hoc context modules that bypass the resource.
- Phoenix is the web interface to the domain, not a second domain layer:
  controllers and LiveViews call Ash actions and render results.
- Use the data layer's guarantees (AshPostgres constraints, identities,
  transactions) for invariants that must never be violated; validations in
  the web layer alone are advisory.

## Phoenix on a Sprite

- Ship a Mix release. The release boots under a Sprites service (see the
  SKILL.md app pattern), runs migrations after its dependencies are
  actually ready, and serves on the Sprite's one HTTP port (8080).
- `/health` does a real database round trip and is wired as the platform
  HTTP check. A static 200 that survives a dead database is a false signal.
- Filter sensitive parameters from logs in **all** environments
  (passwords, passphrases, tokens, secret keys). A passphrase that leaks
  into development logs in plaintext is the same bug as one in production
  logs; it was caught exactly once that way.
