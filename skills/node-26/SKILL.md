---
name: node-26
description: Use when upgrading, validating, or modernizing Node.js projects for Node.js 26, or when answering implementation questions about Node.js 26 features and compatibility. Covers Temporal enabled by default, V8 14.6 Map/WeakMap get-or-insert helpers, Iterator.concat, Undici 8, raw crypto key formats, removed/deprecated APIs, native addon rebuilds, platform minimums, and release/LTS readiness decisions.
---

# Node 26

Practical workflow for adopting Node.js 26 in real projects. Prefer official
Node.js release notes and API docs for date-sensitive details because the v26
Current line can change quickly.

For API patterns, examples, and migration details, read
`references/node-26-upgrade-guide.md`.

## Upgrade Workflow

1. Establish the target.
   - Check `node --version`, `node -p "process.versions"`, package manager
     version, CI images, Dockerfiles, `.nvmrc`, `.node-version`, `mise`,
     Volta, and `package.json` `engines`.
   - Treat Node.js 26 as Current until it reaches LTS. For production services
     already on an LTS line, recommend waiting for the LTS handoff unless the
     user explicitly wants Current or needs a v26 feature.

2. Scan compatibility before changing code.
   - Search for removed or risky APIs:

     ```bash
     rg -n "_stream_(readable|writable|duplex|transform|passthrough|wrap)|writeHeader\\(|--experimental-transform-types|module\\.register\\(|\\blocalStorage\\b" .
     ```

   - Search for native addon or prebuild risk:

     ```bash
     rg -n "node-gyp|binding\\.gyp|node-addon-api|\\bnan\\b|prebuild|node-pre-gyp" package.json pnpm-lock.yaml package-lock.json yarn.lock .github Dockerfile* 2>/dev/null
     ```

3. Adopt Node 26 APIs only where they simplify real code.
   - Use `Temporal` for business dates, time zones, DST-sensitive scheduling,
     and removing date libraries when the runtime target is Node >= 26.
   - Use `Map`/`WeakMap` get-or-insert helpers for cache, grouping, counting,
     and object metadata patterns.
   - Use `Iterator.concat` for synchronous lazy iterable composition.
   - Use raw crypto key formats only when the project already handles direct
     key material.

4. Verify with the actual target runtime.
   - Install dependencies with Node.js 26, rebuild native addons, run tests,
     type checks, linters, and a smoke test of startup plus key workflows.
   - If dependencies do not declare Node.js 26 support, test them under v26
     rather than assuming compatibility.
   - For production rollout guidance, call out Current vs LTS risk explicitly.

## Gotchas

- `Map.prototype.getOrInsertComputed()` is synchronous. If the factory returns
  a Promise, the Promise is stored; it is not awaited.
- `Iterator.concat()` handles synchronous iterables. For streams, paginated API
  clients, async cursors, or other async iterables, use an async generator.
- `Temporal` has distinct types. Choose `PlainDate`, `PlainDateTime`,
  `ZonedDateTime`, or `Instant` based on the domain instead of translating every
  `Date` call mechanically.
- `localStorage` no longer has a useful unconfigured in-memory fallback in
  Node.js 26. Current docs say accessing it without `--localstorage-file`
  throws a `DOMException`; configure persistence or avoid the global.
- `module.register()` is runtime-deprecated. Do not blindly rewrite complex
  loader hooks; check the current `node:module` customization hooks docs.
- Native addons need fresh v26 builds. `NODE_MODULE_VERSION` is 147 for
  Node.js 26.0.0.

## Output Style

- For upgrade requests, return a risk-ordered checklist with exact files and
  commands to run.
- For code changes, keep replacements narrow and explain why each Node 26 API
  improves the existing code.
- For release-status answers, include the concrete Node.js dates and note when
  a claim depends on the current release line.
