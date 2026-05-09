# AURA Response Rendering

This document explains AURA's public, standard AI-app response rendering mechanisms. It does not describe or claim any private ChatGPT/OpenAI backend internals.

## Streaming / Typing Mechanism

AURA keeps `POST /api/chat` as the source of truth.

`POST /api/chat/stream` is an SSE wrapper around the same trusted chat path:

- `start` event announces a request id and whether text will stream;
- `chunk` events send stable text chunks for normal assistant replies;
- `final` event sends the full original chat payload, including metadata, action trace, document delivery, and status;
- `error` event reports recoverable request errors without crashing the UI.

Document and action-card responses are not streamed awkwardly. Their cards are attached on the final event.

## Frontend Incremental Rendering

`interface/web_v2/app.js` uses `fetch()` with a readable stream for `/api/chat/stream`.

Behavior:

- a temporary assistant message is created immediately;
- chunks append to that message progressively;
- the conversation stays pinned near the newest response;
- the Stop control aborts the active request when possible;
- if streaming is unavailable, AURA falls back to `/api/chat`.

## Markdown Rendering

The web renderer supports:

- headings;
- bold and italic emphasis;
- bullet and numbered lists;
- inline code;
- fenced code blocks;
- blockquotes;
- simple markdown tables.

Safety rule: user/model text is inserted with `textContent` or text nodes. AURA does not execute code and does not trust markdown as HTML.

## Code Blocks

Fenced code blocks render as readable artifact-like blocks with:

- monospace font;
- language label when present;
- preserved indentation;
- copy-code button.

Copying code uses the Clipboard API when available and falls back to a temporary textarea copy path.

## Typography / Font Stack

The UI uses:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Code uses:

```css
font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
```

Fonts are referenced as normal CSS stacks; proprietary font files are not bundled.

## Document Artifacts

Document generation responses stay artifact-first:

- title;
- type;
- preview snippet;
- format chips;
- direct downloads;
- copy preview when available.

The UI does not display raw internal JSON. Download links remain served by the backend's document access rules.

## Image Generation Provider Abstraction

`tools/image_generation.py` defines:

- `detect_image_generation_request(text)`;
- `get_image_generation_status()`;
- `generate_image(prompt, style=None, size=None)`.

Current truth:

- no verified image provider adapter is active by default;
- AURA returns a clear unavailable response;
- no fake placeholder image is produced.

Future providers can include OpenAI image generation, local Stable Diffusion, or another configured image provider. A provider must pass a real adapter implementation before the UI should claim image generation works.

## Writing Tone Shaping

`brain.response_engine.shape_response_for_task()` removes weak openings while preserving useful markdown.

Tone goals:

- greeting: short and natural;
- explanation: structured but concise;
- academic assignment: formal and organized;
- report: professional;
- code: direct, with code blocks where useful;
- action result: short and factual;
- blocked action: calm safety explanation;
- degraded response: honest but helpful.

Avoided patterns:

- "Certainly";
- "As an AI";
- "I'd be happy to";
- "Here's some information";
- generic filler before the answer.

## Safety Rules

- Do not copy proprietary assistant internals.
- Do not execute rendered code.
- Do not render model text as trusted HTML.
- Do not fake generated images.
- Do not show unsupported conversions as working.
- Keep `/api/chat` stable for non-streaming clients.

