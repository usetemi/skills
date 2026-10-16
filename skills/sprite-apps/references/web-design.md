# Web design

The interface reference for sprite-apps builds. Two philosophies anchor it:
**less is perfection**, and **motion directs attention**. Run any screen
through this in about five minutes, on a real phone, one screen at a time.
Three fails in one section means redesign that section.

## 1. Less is perfection: subtract first

- One job per screen, statable in one sentence. If not, split the screen.
- Subtraction pass: remove one element, input, or feature. If nothing
  breaks, it stays out. A product is done when nothing more can be taken
  away.
- Complexity is moved, not dumped on the user: the system infers, defaults,
  and autofills. (Tesler's Law)
- Less at a time, not less overall: dense tasks keep their data, revealed
  progressively.
- Affordance survives subtraction, and there is no memory tax: a
  first-timer can tell what is clickable, and nothing must be remembered
  from the previous screen. Recognize, do not recall.

## 2. Motion directs attention: one mover only

- One thing animates at a time. Two competing motions direct attention to
  neither.
- Every animation has a job: direct attention, show origin/destination,
  show cause and effect, or confirm an action. No job, no motion.
- Feedback is fast: press and click responses land in under 400 ms.
- Physics matches the stakes. Bouncy means playful and low-stakes;
  payments, deletes, and medical submissions settle firmly.
- Respect `prefers-reduced-motion`: the screen still works, and nothing
  essential is conveyed by movement alone.

## 3. Typography and reading

- Measure: 45–75 characters per line, 66 ideal, roughly 9–12 words. In
  CSS: `max-width: 65ch`.
- Leading: 1.4–1.6 for body text, tighter for headlines. A wider measure
  needs more leading.
- Tracking: never letterspace lowercase body text; do add it to all-caps
  labels.
- Hierarchy by eye: at arm's length, the key text is unmistakably the
  biggest or boldest. One dominant element per view; two highlights equal
  zero highlights. (Von Restorff effect)
- People judge an experience by its peak and its ending. The confirmation
  screen earns disproportionate care. (Peak-End Rule)

## 4. Human factors

- Jakob's Law: navigation and flows work the way users already expect
  from other sites. Familiar beats original here.
- Hick's Law: decision time grows with choices. Fewer, clearer options,
  or a strong default, at every decision point.
- Working memory is about 4 chunks, not 7. Chunk lists and forms; never
  ask for four-plus ungrouped things at once.
- Gestalt: spacing is syntax. Close together reads as a group; the
  spacing scale is the information architecture.

## 5. Layout and targets

- Touch targets at least 44 pt (iOS) / 48 dp (Android), with space
  between neighbours. Bigger and closer is faster to hit. (Fitts's Law)
- Alignment and contrast hold: edges line up on a grid, and body text
  reads in bright light, not just a dark room.

## 6. Copy is interface

- Buttons say what happens: the outcome, not "OK" or "Submit".
- Errors say what to do next, in plain language, next to the field that
  caused them.
- Empty states explain and act: what belongs here, and the one action
  that fills it.
- No label needs a manual. Rewrite it.

## 7. States and forgiveness

- Postel's Law: accept any reasonable phone, date, or number format and
  normalize it yourself. Never reject valid input over formatting.
- All four states are designed: empty, loading, error, and partial. Not
  just the happy path.
- Undo beats confirmation: destructive actions are reversible where
  possible; confirmations only where they are not.
- Beauty is not a pass: a polished screen with a broken core flow still
  fails.

## Verdict

Count the unticked boxes. 0–2: ship it. 3–5: fix before users see it.
6+: the screen does too much; return to Section 1 and subtract. Fix order:
job, states, type, motion.

Instant fails, any one of them:

- Two things animating for attention at once
- A line of body text wider than 75 characters
- An error that blames formatting the user got right

## Go deeper, in order

* Laws of UX (Jon Yablonski) · Butterick's *Practical Typography* ·
  Norman, *The Design of Everyday Things* · *Refactoring UI*
