# Node 26 Upgrade Guide

Use this reference for Node.js 26 upgrade planning, migration scans, and
targeted API adoption. Verify precise release status against official Node.js
docs if the user asks what is current today.

Official anchors:
- Node.js 26.0.0 release notes: `https://nodejs.org/en/blog/release/v26.0.0`
- Node.js API docs: `https://nodejs.org/docs/latest/api/`

## Release Posture

Node.js 26.0.0 shipped on 2026-05-05 as the Current release line. The initial
release notes say v26 is scheduled to enter LTS in October 2026.

Default guidance:
- New projects, prototypes, CI compatibility checks, and library validation can
  use v26 early.
- Production services on an LTS line should usually wait for v26 LTS unless
  they need a v26 feature or have explicit approval for Current.
- Treat v25 as superseded by v26; odd-numbered Node.js majors do not become LTS.

## Temporal

Node.js 26 enables the global `Temporal` API by default. Use it when code needs
clear calendar/date/time semantics, not as a mechanical replacement for every
`Date`.

Type selection:
- `Temporal.PlainDate`: calendar dates without time or zone.
- `Temporal.PlainDateTime`: local date/time without a time zone.
- `Temporal.ZonedDateTime`: wall-clock event plus IANA time zone.
- `Temporal.Instant`: absolute point in time.
- `Temporal.Duration`: typed elapsed or calendar duration.

Calendar math:

```js
const invoiceDate = Temporal.PlainDate.from('2026-01-31')
const dueDate = invoiceDate.add({ months: 1 })
const lastDay = invoiceDate.with({ day: invoiceDate.daysInMonth })

console.log({ invoiceDate: String(invoiceDate), dueDate: String(dueDate), lastDay: String(lastDay) })
```

DST-sensitive scheduling:

```js
const start = Temporal.ZonedDateTime.from('2026-03-28T20:00[Europe/Dublin]')

const sameWallTimeTomorrow = start.add({ days: 1 })
const exactly24HoursLater = start.add({ hours: 24 })

console.log(String(sameWallTimeTomorrow))
console.log(String(exactly24HoursLater))
```

Sorting:

```js
const dates = ['2026-12-15', '2026-05-08', '2026-08-01']
  .map((value) => Temporal.PlainDate.from(value))

dates.sort(Temporal.PlainDate.compare)
```

Migration notes:
- Remove `@js-temporal/polyfill` only when all supported runtimes are Node >= 26
  and dependencies do not still need the polyfill.
- Convert at boundaries. Avoid passing Temporal objects through APIs that expect
  legacy `Date` instances unless the boundary explicitly supports them.
- For persistence and wire formats, prefer explicit ISO strings and document the
  expected Temporal type.

## Map And WeakMap Get-Or-Insert

V8 14.6 in Node.js 26 includes `Map.prototype.getOrInsert()`,
`Map.prototype.getOrInsertComputed()`, and matching `WeakMap` helpers.

Use `getOrInsertComputed` when the default is expensive or should only be
created on a cache miss:

```js
const profileCache = new Map()

function getProfile(userId) {
  return profileCache.getOrInsertComputed(userId, () => buildProfile(userId))
}
```

Use it for grouping:

```js
const byCustomer = new Map()

for (const order of orders) {
  const bucket = byCustomer.getOrInsertComputed(order.customerId, () => [])
  bucket.push(order)
}
```

Use `getOrInsert` when the default is cheap:

```js
const counts = new Map()

for (const word of words) {
  counts.set(word, counts.getOrInsert(word, 0) + 1)
}
```

Use `WeakMap` helpers for metadata attached to objects you do not own:

```js
const metadata = new WeakMap()

function markSeen(object) {
  const entry = metadata.getOrInsert(object, {})
  entry.seenAt = performance.now()
}
```

Async gotcha: `getOrInsertComputed` stores the exact return value. If the
factory is `async`, the cached value is a Promise. That can be useful for
in-flight request batching, but it must be deliberate.

## Iterator.concat

`Iterator.concat(...iterables)` composes synchronous iterables lazily and returns
a standard Iterator, so iterator helpers can be chained.

```js
function* range(start, end) {
  for (let value = start; value < end; value += 1) {
    yield value
  }
}

const firstFiveEven = Iterator.concat(range(0, 100), range(200, 300))
  .filter((value) => value % 2 === 0)
  .take(5)
  .toArray()
```

Use it instead of spreading into arrays when the source can be large or lazy.
Do not use it for async iterables:

```js
async function* concatAsync(...iterables) {
  for (const iterable of iterables) {
    yield* iterable
  }
}
```

For Node streams, prefer stream/readline APIs or convert deliberately to async
iterables rather than forcing them through synchronous iterator helpers.

## Crypto Raw Key Formats

Node.js 26 adds raw key format support for `crypto.createPrivateKey()`,
`crypto.createPublicKey()`, and key export paths. Current docs mark raw key
formats as active development, so use them when they remove real key-encoding
ceremony in code that already handles raw key material.

Import an Ed25519 raw private key:

```js
import { createPrivateKey } from 'node:crypto'

const privateKey = createPrivateKey({
  key: rawPrivateKeyBytes,
  format: 'raw-private',
  asymmetricKeyType: 'ed25519',
})
```

Export generated Ed25519 keys:

```js
import { generateKeyPairSync } from 'node:crypto'

const { publicKey, privateKey } = generateKeyPairSync('ed25519')

const rawPublicKey = publicKey.export({ format: 'raw-public' })
const rawPrivateKey = privateKey.export({ format: 'raw-private' })
```

Use Ed25519 signing context only when the protocol needs domain separation:

```js
import { sign, verify } from 'node:crypto'

const context = Buffer.from('payments-v1')
const signature = sign(null, message, { key: privateKey, context })
const isValid = verify(null, message, { key: publicKey, context }, signature)
```

Never invent crypto protocols just because raw formats are easier in v26.

## Runtime And Dependency Changes

V8 and Undici:
- V8 is updated to 14.6.202.33 in v26.0.0.
- Undici is updated to 8.0.2 in v26.0.0. Built-in `fetch()` consumers should
  run HTTP integration tests, but no rewrite is implied by the version bump.

Native addons:
- `NODE_MODULE_VERSION` is 147 in v26.0.0.
- Rebuild native addons and verify prebuilt binaries under Node.js 26.

Build/platform checks:
- Building Node.js from source requires GCC 13.2 or newer.
- Python 3.9 is no longer supported for building Node from source; use Python
  3.10 or newer.
- Windows source builds require the Windows 11 SDK.
- Power 8 on AIX/IBM i and z13 support were dropped.

## Breaking-Change Scan

Run this before upgrading a project:

```bash
rg -n "_stream_(readable|writable|duplex|transform|passthrough|wrap)|writeHeader\\(|--experimental-transform-types|module\\.register\\(|\\blocalStorage\\b" .
```

Handle findings this way:
- `_stream_*` imports: replace private modules with public `node:stream`
  exports.
- `writeHeader(`: replace with documented `writeHead(`.
- `--experimental-transform-types`: remove the flag. If code relied on enum,
  namespace, or decorator transforms, add a real TypeScript build step such as
  `tsc`, `tsx`, or `swc`.
- `module.register(`: expect a runtime deprecation warning in v26. Consult
  current `node:module` customization hooks docs before rewriting loader hooks.
- `localStorage`: do not rely on unconfigured runtime storage. Current docs say
  accessing `localStorage` without `--localstorage-file` throws a
  `DOMException`; configure a storage file or avoid the global in Node code.

## Verification Checklist

- Run dependency install under Node.js 26 with the project's package manager.
- Rebuild native addons and regenerate lockfiles only if the package manager
  requires it.
- Run unit tests, integration tests, type checks, lint, and application startup.
- Test any date/time, scheduling, cache, HTTP, crypto, and loader-hook paths
  touched during migration.
- Check CI, Docker, deploy images, and `engines` constraints before claiming
  the project supports Node.js 26.
