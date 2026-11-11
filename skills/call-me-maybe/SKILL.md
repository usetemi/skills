---
name: call-me-maybe
description: Build a reusable voice layer for AI agents on Cartesia Managed Agents: give an agent you normally type to (a personal assistant, a coworker agent, a coding agent) the ability to call the user by phone, hold a live spoken conversation, and hand back a transcript. Agent + webhook server + optional mid-call tools, with a no-hangup configuration and a WebSocket simulated caller for testing without dialing anyone. Continually a prototype. Use when the user wants to talk to an AI agent by phone instead of typing, wants an agent that calls them to coach, interview, remind, teach, or check in, or asks to build, debug, or extend a Cartesia voice agent or its call webhooks.
---

# call-me-maybe: a voice layer for calling AI agents

## Status: continually a prototype

This skill is a living prototype, not a finished platform. It documents the pattern exactly as proven in real calls (2026-11-10/11) and keeps changing as the voice layer gets reused for more agents. Treat every detail as the current best-known version: when something fails, verify the path against the live API before improvising, and fold what you learn back into this file.

## What this is

The point is a **reusable voice layer for AI agents**: an agent you normally type to (a personal assistant like Muse, a coworker agent, even a coding agent like Claude Code) becomes someone you can talk to on the phone. The agent calls you, you have a real conversation out loud, and a transcript comes back. Talking instead of typing is the product; Cartesia is today's implementation of the layer.

A Cartesia **Managed Agent** does the talking: it places an outbound call from a Cartesia phone number, runs the conversation in real time (native turn detection, streaming TTS), and emits events to a webhook server you control. Your server stores the transcript and can expose **webhook tools** the agent calls mid-conversation (fetch data, start a background job, look something up).

Two proven shapes:

- **One-off tutor / companion** — agent with instructions only, no tools. Fastest path from idea to ringing phone.
- **Coached session with a slow advisor** — the agent interviews; a second, stronger model reviews notes asynchronously behind two tools (`start_advisor` fires it and returns immediately, `fetch_updates` delivers its note later). The call never blocks on the slow model.

## Architecture

```
                ┌──────────────────── Cartesia cloud ────────────────────┐
                │  Managed Agent (prompt/config frozen at call start)    │
                │  model + voice + instructions + system tools           │
                └──────┬──────────────────────┬──────────────────┬───────┘
              phone audio               event webhook        webhook tools
                       │                      │                  │
                 the callee          your server (host)    your server (host)
                                     transcripts, logs     per-call state,
                                                           background jobs
```

- Per-call context goes in as **dynamic variables** at call setup. There is **no live prompt steering** mid-call: a call stays on the config it started with. Steer through tools (the agent polls a fetch tool) or pre-authorize a knowledge source in the prompt.
- The host in the reference implementation is a Fly Sprite running a stdlib-only Python server with JSON state files on disk. Any always-on host with a public HTTPS URL works.

## Access

- All API calls go through the Sprites gateway connection for Cartesia (a `custom_api` connection whose display name is `cartesia`): GET `https://api.sprites.dev/v1/gateway/list` from inside a sprite labeled `conn:cartesia`, match the connection, use its `gateway_base_url` as the API base. Gateway calls must run **inside a labeled sprite**; the org token cannot call gateway endpoints from outside.
- Send header `Cartesia-Version: 2026-08-14` on every API call.
- Secrets (webhook secret, tool bearer token) live in mode-0600 files next to the server, never in code, prompts, or git.

## Build order

Do the preparatory work in this order; each step's output feeds the next.

### 1. Webhook server

Endpoints the reference server implements:

- `POST /cartesia-webhook` — call events. Verify the `X-Webhook-Secret` header against your stored secret. On `call_completed` / `call_failed`, store the transcript keyed by the agent call id. Log every event as one JSON line.
- `POST /tools/<name>` — one endpoint per webhook tool (step 2). Verify `Authorization: Bearer <tool token>`.
- `GET /health`, `/status`, `/transcript` — operator reads, protected by the webhook secret.

Keep the server dependency-free (stdlib only) unless you have a reason; state as JSON files is enough at this scale.

### 2. Webhook (Cartesia side) and tools

- Create the event webhook: `POST /agents/webhooks` with `{display_name, url: <server>/cartesia-webhook, secret}`. **The path is `/agents/webhooks`, not `/v1/agents/webhooks`** — the `/v1` form 404s.
- Create each tool: `POST /v1/agents/tools` with `type: "webhook"`, an `api_schema` pointing at your server endpoint, bearer-secret authentication, `execution_mode: "immediate"`, `pre_tool_speech: "off"`, and a `response_timeout_secs` around 20.
- Key per-call state by the `system__conversation_id` dynamic variable: declare a `conversation_id` string property with `"dynamic_variable": "system__conversation_id"` in the tool's request schema and have the server key its state files by it.
- **Dynamic-variable parameters cannot be `required`** — the API rejects the tool if they are. Put them in `properties`, leave them out of `required`.
- Long work never runs inside a tool call. The tool acknowledges in under a second and the work runs in a background thread; a second fetch tool returns the result when ready (or a "still thinking / proceed without it" message). Retry transport errors up to 3 times — a single gateway stall otherwise silently loses the result.

### 3. Agent

`POST /v1/agents` with `{name, config}`. The config that works:

- `instructions` — the full behavioral prompt (see "Writing instructions" below).
- `initial_message` — the agent speaks first; write the actual greeting.
- `model: {id: "claude-sonnet-5"}`, `language: {primary: "en"}`, `timezone` set to the callee's.
- `audio.input.keyterms` — names and jargon the recognizer should expect (people, product names, domain terms). This measurably helps transcription.
- `audio.output.voice_id` — pick once, reuse across agents for a consistent persona.
- `speculative_generation: true`, `prompt_optimization: false` (you wrote the prompt; don't let the platform rewrite it).
- `turn.inactivity_end_call_secs` — **must be ≤ 240**; the API rejects higher values. `inactivity_check_in_secs: null` (no robotic "are you still there?").
- `system_tools`:
  - `end_call: null`, `send_dtmf: null`, `transfer_to_number: null` — disabled. **The agent never hangs up; the callee ends the call.** This is a product decision, not an oversight: an agent that can hang up will eventually hang up on the user mid-thought.
  - `skip_turn` — enabled, with a description telling the agent to stay silent when the caller's turn is clearly unfinished (trailing off, thinking aloud). `wait_timeout_secs: 120`.
  - `voicemail_detection` — enabled, usable only before any live human has spoken, `pre_tool_speech: "off"`, with a message of **at most ~15 seconds** of speech: who is calling and what about, nothing more.
- Attach `tools: [{id: ...}]` and `event_webhook_id` from step 2.
- **Verify by readback**: `GET /v1/agents/{id}` and confirm tools, webhook id, and system tool keys are what you sent. If the first create ran before the tools/webhook existed, PATCH the agent with the missing pieces instead of creating a duplicate.

### 4. Place the call

`POST /agents/calls` (note: no `/v1`) with:

```json
{
  "from_number_id": "<Cartesia phone number id>",
  "agent_id": "<agent id>",
  "ringing_timeout_seconds": 60,
  "outbound_calls": [
    {"to_number": "+1...", "dynamic_variables": {"session_date": "Tuesday, November 10, 2026"}}
  ]
}
```

A 200 with an `agent_call_id` per call means the dial is placed, not that the callee answered — the webhook events tell you what actually happened.

### 5. After the call

Read the stored transcript from your server. Terminal WebSocket test sessions (below) arrive as `call_failed` / `client_disconnected` — expected, not an error.

## Testing without calling anyone

Never test by dialing the user. Use a **simulated caller over Cartesia WebSocket**:

1. Generate the synthetic caller's lines as audio with Cartesia TTS ahead of time.
2. Create a call-bound WebSocket session through the API and connect — the WS URL needs `&cartesia_version=2026-08-14` appended or the handshake 400s.
3. Stream the lines, record every agent turn and tool call, assert on the transcript: did the right tools fire, in the right order, with faithful parameters?
4. Run the WS client from a **normal host, not from inside a sprite**: the sprite network path kills long-lived WebSockets after ~1–2 minutes (verified against an echo server). The prep step that mints the session token can still run inside the sprite; the token is single-use and the client has a few minutes to connect.

There is **no tool-test API** (`/v1/agents/tools/{id}/test` 404s in every shape tried). The simulated caller is the test path; don't burn time rediscovering this.

## Writing instructions for a voice agent

- Write for the ear: short spoken sentences, no lists, no formatting, nothing that only makes sense on a screen.
- State the conversation norms explicitly: don't repeat back what the caller said, don't summarize unless asked, answer the question asked then stop and let them steer, offer one follow-up direction at a time.
- Give the agent its knowledge in the prompt for a one-off agent (a few thousand words is fine); for anything that changes, prefer a fetch tool over prompt stuffing.
- Tell it what to do at the edges: unsure → say so and reason aloud; goodbye → say goodbye warmly and let the callee end the call; silence → wait (skip_turn), don't narrate.

## Pitfalls (each one cost real time once)

- `POST /v1/agents/webhooks` 404s; the correct path is `/agents/webhooks`. Calls are `/agents/calls`, also without `/v1`. Tools and agents themselves are `/v1/...`. Mixed versioning is real; copy paths from this skill, not from intuition.
- `inactivity_end_call_secs` above 240 → 400 "Too big".
- A `required` dynamic-variable parameter → tool creation rejected.
- Reading a GitHub-style "created" response as success without the `GET` readback — attach steps fail silently; read back every time.
- Voicemail messages that explain the whole product: if the call lands on voicemail you get one short message, ~15 seconds. Anything longer gets cut off and sounds broken.
- Letting the agent end calls. Disable `end_call` unless the use case genuinely requires the agent to hang up (e.g. outbound screening with a hard script), and if you enable it, say why in the instructions.
- Testing against the user's real phone "just once to check." The simulated caller exists precisely so this never happens during development.

## Reference implementation

Built 2026-11-10/11, two production callers on this exact pattern:

- Storyworthy coach — nightly call that interviews the user about their day and shapes a one-minute story; the advisor variant (Fable behind `start_advisor` / `fetch_updates` webhook tools), webhook transcripts stored per call.
- Cold-drip tutor — one-off, instructions-only agent built and called within the hour to teach the user about the coffee brewer in front of them.

Host layout (per caller): `server.py` (webhook + tools + operator reads), `build_agent.py`, `place_call.py`, `instructions.txt`, `secret.txt` / `tool_token.txt` (0600, uncommitted), state and transcripts as JSON on the host disk.
