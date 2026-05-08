# AURA

Autonomous Universal Responsive Assistant

AURA is a local-first, JARVIS-style assistant prototype that combines chat, document generation, controlled desktop actions, voice scaffolding, memory, and a safety-first execution model.

AURA is currently a **Level 3 / early Level 4 JARVIS-style assistant prototype**. It is useful for controlled local demos and continued development, but it is **not** a finished production assistant and it is **not** real JARVIS-level autonomy.

## What AURA Is

- A FastAPI-based assistant runtime with a modern `web_v2` interface.
- A controlled assistant system that can answer, plan, generate documents, launch safe apps, run limited browser actions, and perform permission-gated OS automation.
- A truth-first project: unsupported, unsafe, or dependency-based capabilities should be labeled clearly instead of pretending to work.

## What AURA Is Not

- Not a production-ready personal AI operating system.
- Not a fully autonomous desktop controller.
- Not a Level 5 real JARVIS system.
- Not safe for unrestricted passwords, banking, payments, destructive file operations, or arbitrary shell execution.
- Not guaranteed to run every voice, OCR, provider, or automation feature on every machine without local dependencies.

## Current Status

Status: active local development and controlled demo readiness.

The stable path is:

`run_aura.py` -> FastAPI app in `api/api_server.py` -> runtime/brain/tools/security modules -> `interface/web_v2`

The project currently has a broad automated test suite. At the latest stable milestone, the local unittest suite covered more than 250 tests, with the recent full run reporting 293 passing tests.

## Key Features

- Chat-first AURA interface with orb state presence.
- Authenticated and public session handling.
- Scoped memory and personalization safeguards.
- Provider-backed response generation with degraded fallback behavior.
- Document generation for notes, assignments, PDF, DOCX, TXT, and PPTX outputs.
- Direct document download delivery and preview cards.
- Controlled desktop app launching for allowlisted apps.
- Controlled browser actions such as safe URL/search flows.
- Permission-gated OS automation wrappers for limited actions.
- Basic screen capture and OCR-based safety checks.
- Browser push-to-talk and desktop voice runtime scaffolding.
- Trust model for safe, private, sensitive, and critical actions.

## Architecture Overview

```text
User input
  -> API layer
  -> identity/session context
  -> intent routing
  -> permissions/trust check
  -> provider, document, action, automation, or fallback path
  -> response shaping
  -> memory update where safe
  -> web_v2 delivery
```

Important paths:

- `run_aura.py` - supported local launcher.
- `api/api_server.py` - live FastAPI API.
- `brain/` - runtime orchestration, response quality, providers, traces.
- `security/` - sessions, permissions, trust enforcement.
- `memory/` - scoped memory and personalization data.
- `tools/` - documents, desktop control, browser actions, OS automation, screen capture.
- `voice/` - browser-independent desktop voice runtime scaffolding.
- `interface/web_v2/` - current browser interface.
- `tests/` - regression and system behavior tests.

## Safety and Trust Model

AURA uses trust levels to prevent unsafe behavior:

- `safe` - normal chat, document generation, safe app open/search.
- `private` - user/account information and memory-related actions.
- `sensitive` - keyboard/mouse control, typing into apps, screen-aware automation.
- `critical` - passwords, payments, banking, destructive actions, account/security changes.

Critical actions must remain blocked or require a stronger verification flow. AURA must not silently control the system.

## Setup

Prerequisites:

- Windows is the primary development target.
- Python 3.10+ recommended.
- Node.js for JavaScript syntax checks.
- Optional local dependencies for voice, OCR, DOCX/PDF/PPTX export, and automation.

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file only for your own machine. Do not commit secrets.

## Run

```powershell
python run_aura.py
```

Then open:

```text
http://127.0.0.1:5000/
```

Useful health check:

```powershell
python tools/health_check.py
```

## Test

```powershell
python -m py_compile run_aura.py api\api_server.py
node --check interface\web_v2\app.js
node --check interface\web_v2\auth.js
python -m unittest discover -s tests -p "test_*.py"
```

## Demo Commands

Safe demo commands:

- `hello`
- `explain artificial intelligence simply`
- `write a 3 page assignment on climate change`
- `make notes on transformers`
- `open chrome and search AI trends`
- `open notepad and type hello` then approve control if the environment supports it
- `type my password` to show critical blocking

Avoid demoing:

- Banking, payment, password, or destructive workflows.
- Full always-on voice claims unless the desktop voice runtime is explicitly enabled and verified.
- Broad screen understanding beyond OCR-level context.
- Unsupported apps or arbitrary shell commands.

## Screenshots

Screenshots are not committed in this cleanup pass. Add verified screenshots later under `docs/screenshots/` and reference them here.

Suggested screenshots:

- AURA web_v2 chat shell.
- Document delivery card.
- Action plan approval card.
- Desktop voice status panel.
- Blocked critical action example.

## Limitations

- Voice reliability depends on local microphone, STT, TTS, and optional runtime dependencies.
- Provider reliability currently depends heavily on configured provider keys, especially Groq in local development.
- OCR screen awareness is useful for safety checks but not deep visual understanding.
- OS automation is intentionally narrow and permission-gated.
- Long-form document quality is improving but still needs stronger research and references.
- Memory is scoped and safer than earlier builds, but long-term personalization still needs more hardening.

## Roadmap

Near-term focus:

- Runtime reliability and Windows startup polish.
- Memory and identity isolation.
- Desktop voice reliability.
- Provider health truth and fallback quality.
- Document intelligence polish.
- Screen awareness and automation robustness.
- UI/orb polish and demo packaging.

See `ROADMAP.md` for the full plan.

## License / Status

No license file is currently present. Until a license is added, this repository should be treated as private/all-rights-reserved by default.

