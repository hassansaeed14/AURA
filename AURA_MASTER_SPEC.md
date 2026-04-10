# AURA Master Spec

## Project Name
AURA — Autonomous Universal Responsive Assistant

## Project Type
A JARVIS-style AI assistant system, not a chatbot.

## Core Goal
AURA should evolve into a real assistant that can:

- Understand natural language
- Handle messy input, typos, and short forms
- Process multi-command requests
- Use memory and learning
- Reason, plan, and execute tasks
- Interact with systems safely
- Improve over time

## Core Pipeline
Perceive -> Understand -> Decide -> Act -> Reflect -> Improve

## Design Principles
- Stability over hype
- Modular backend
- Terminal-first workflow
- Recordable progress
- Privacy-first design
- Trust-based interaction
- Controlled automation

## Trust Model
Actions are categorized:

- `safe` -> auto allow
- `private` -> ask confirmation
- `sensitive` -> session approval
- `critical` -> PIN or password

AURA should not ask for permission on everything.
Only risky actions should trigger confirmation.

## Privacy Model
- Minimal developer access
- No exposure of user personal data by default
- Local control where possible

## Interface Goal
AURA should feel like an AI OS, not a chat box.

Support:

- Chat
- Memory
- Intelligence
- Autonomy
- Tasks
- History
- Settings
- Multiple modes

## Important Rules
- Do not reduce AURA to a chatbot
- Do not fake capabilities
- Respect architecture consistency
- Keep the system realistic and expandable

## Implementation Notes
This file is the canonical high-level product spec for AURA.

When making changes, prefer:

- Real capability over simulated marketing behavior
- Explicit trust and permission boundaries
- Modular components with clear ownership
- Verifiable execution paths
- Safe fallback behavior when a capability is unavailable

## Implementation Rules
AURA must be built as a hybrid and increasingly real assistant system.

Implementation priority:

- `real`
- `hybrid`
- `placeholder`

Preferred implementation order:

1. Detect intent
2. Parse data
3. Apply rules
4. Check permissions
5. Execute real action
6. Enhance with AI

Correct pattern:

- Real or rule-based foundation
- Stateful system behavior
- AI enhancement

Strictly forbidden:

- Fake autonomy
- Fake purchases
- Fake system control
- Fake memory
- Fake permissions
- Fake execution

Wrong way:

- "LLM explains what it would do"

Right way:

- System actually does it
- Or clearly says it is not implemented yet

Placeholder features must:

- Be clearly marked
- Never pretend they are real
- Define a future integration path

## UI Rule
Frontend must not overclaim backend capability.

The UI must not strongly claim intelligence, autonomy, security, purchases, or execution unless the backend actually supports it or it is clearly marked as placeholder.

## Current State
Project root:

- `D:\HeyGoku`

Structure:

- `brain/`
- `agents/`
- `memory/`
- `api/`
- `interface/web/`
- `voice/`
- `config/`
- `security/`

Core system:

- `brain/core_ai.py` -> main brain
- `brain/intent_engine.py` -> intent detection
- `brain/understanding_engine.py` -> input cleaning
- `brain/decision_engine.py` -> routing decisions
- `brain/response_engine.py` -> fallback LLM behavior

Features built:

- Multi-command handling
- Memory system
- Learning system
- Reasoning layer
- Planning and execution
- Web interface
- Auth system
- Tasks and reminders
- Screenshot and file system

Current issues:

- Weak typo handling
- Permission not always triggered
- Memory extraction bugs partially fixed
- Fallback to general too often
- UI partially placeholder
- Purchase flow not real yet

Security status:

- Permission engine started
- No PIN system yet
- No locked chats yet

Next builds:

- PIN system
- Locked chats
- Permission UI
- Real intelligence panel
- Real autonomy panel
- PC control in the future

## Support Chats
AURA support chats:

1. AURA Backend Builder
   Writes backend code and upgrades or refactors files.
2. AURA Code Reviewer
   Checks code quality and safety.
3. AURA Output Tester
   Analyzes runtime and output behavior.
4. AURA Error Explainer
   Explains bugs clearly.
5. AURA Interface Architect
   Designs the frontend system.

Global rules:

- Follow `AURA_MASTER_SPEC`
- Follow implementation rules
- Do not guess missing architecture
- Do not fake features
- Keep code modular and stable

Builder is final authority:

- Only Backend Builder writes final code
