# AURA
## Autonomous Universal Responsive Assistant
**A real JARVIS-style AI OS. Not a chatbot.**

---

## What is AURA?

AURA is a private JARVIS-style AI operating system.
It understands your voice, thinks, executes real tasks,
remembers everything, and speaks back to you.

It is not a chatbot. It is not a prompt wrapper.
It is a real system with a real brain, real memory,
real agents, and real execution paths.

Core pipeline:
Perceive -> Understand -> Decide -> Act -> Reflect -> Improve

---

## Current Status — v1.0-dev

| Component | Status |
|-----------|--------|
| Web interface | Working |
| Brain pipeline | Working |
| Voice input | Working |
| Voice output | Working |
| Chat memory | Working |
| Auth and login | Working |
| PIN system | Working |
| Locked chats | Working |
| 256 agent system | Working |
| Gemini main brain | Coming soon |
| ElevenLabs voice | Coming soon |
| Vector memory | Being fixed |
| Tavily web search | Coming soon |

Full honest details in AURA_MASTER_SPEC.md

---

## Quick Start

### What you need
- Windows 10 or 11
- Python 3.10 or higher
- A free Groq API key from console.groq.com

### How to install

Step 1 — Download the project:
Go to the green Code button on this page
Click Download ZIP
Extract the ZIP to any folder

Step 2 — First time setup:
Double click setup_aura.bat
Wait for it to finish

Step 3 — Add your API key:
Find the file called .env.example
Copy it and rename the copy to .env
Open .env with Notepad
Find the line: GROQ_API_KEY=your_groq_key_here
Replace your_groq_key_here with your real Groq key
Save the file

Step 4 — Launch AURA:
Double click AURA.bat
Your browser will open automatically
Go to http://localhost:5000

---

## API Keys — Where to get them

AURA works with just one free API key from Groq.
All other keys are optional and add more features.

Groq — Free — Main AI brain — console.groq.com
Gemini — Free — Smarter reasoning — aistudio.google.com
OpenAI — Paid — Backup brain — platform.openai.com
OpenRouter — Free — Fallback brain — openrouter.ai
Tavily — Free — Web search — tavily.com
AssemblyAI — Free — Voice input — assemblyai.com
ElevenLabs — Free — Premium voice — elevenlabs.io
Replicate — Free — Image generation — replicate.com
Supabase — Free — Cloud database — supabase.com
Qdrant — Free — Vector memory — cloud.qdrant.io
Upstash — Free — Session cache — upstash.com

---

## Project Structure

brain/ — Core AI pipeline and reasoning
agents/ — 256 specialized task agents
memory/ — Memory and history system
api/ — FastAPI backend server
interface/web/ — Web UI with animated ORB
security/ — Auth, PIN, and permissions
voice/ — Voice input and output
config/ — Settings and profiles
tools/ — Execution and system tools
tests/ — Test suite

AURA.bat — Double click to launch
setup_aura.bat — Run once on first install
AURA_MASTER_SPEC.md — Full honest project spec
AURA_VERSION_LOG.md — Version history

---

## How AURA Works

You speak or type something
AURA cleans and understands your input
AURA detects what you want
AURA picks the right agent from 256 agents
The agent executes the real task
The AI provider generates the response
Memory system saves and learns
AURA responds in text and speaks back to you

---

## Security

AURA is a private system.
Only people the owner invites can access it.

Safe actions — execute automatically
Private actions — AURA asks for confirmation
Sensitive actions — need session approval
Critical actions — need confirmation code and PIN

Security features:
- Invite only access with whitelist
- Secure login sessions
- Rate limiting to block brute force attacks
- PIN lock system
- Encrypted locked chats
- Auto lock after inactivity

---

## Known Issues

These are real current bugs.
If you find more please open an issue.

Critical:
- Groq API key needs to be updated — getting 401 error
- Vector memory running in fallback mode

High:
- Security tests have some outdated code
- Provider hub can overclaim readiness

Full list with exact file locations in AURA_MASTER_SPEC.md

---

## What is Coming Next

Fixing now:
- Fix Groq key and restore brain
- Real provider health checks
- Fix vector memory
- Fix auth test problems

Adding next:
- Gemini as main brain
- Dependable voice output
- Real-time web search

Adding later:
- ElevenLabs premium voice
- Supabase cloud database
- Qdrant vector memory

---

## How to Give Feedback

Click the Issues tab at the top of this page
Click New Issue
Choose the right template
Fill in the details

Labels you can use:
bug — something is broken
brain — AI gave wrong response
voice — voice not working
ui — interface problem
security — security issue
memory — memory problem
agent — agent behavior wrong
enhancement — new feature idea

---

## Version History

Started as Hey Goku on Day 01 as a basic terminal AI
Now AURA v1.0-dev — full AI OS with voice memory agents and security

Full history in AURA_VERSION_LOG.md

---

Built by Hassan Saeed

AURA is always online. Always improving.

The goal is not to build a chatbot.
The goal is to build JARVIS.
