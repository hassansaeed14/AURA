# Security Policy

AURA is a local-first assistant prototype with real execution capabilities. Security is part of the runtime, not a UI label.

## Reporting Vulnerabilities

Do not publish sensitive vulnerability details in public issues. Report privately with:

- affected component;
- steps to reproduce;
- impact;
- logs or screenshots if safe;
- suggested mitigation if known.

## Trust Levels

AURA classifies actions before execution.

### Safe

Examples:

- normal chat;
- document generation;
- opening allowlisted apps;
- safe browser URL/search actions.

Safe actions can proceed automatically.

### Private

Examples:

- profile/account state;
- user memory;
- personal preferences.

Private actions must respect user/session scope.

### Sensitive

Examples:

- keyboard or mouse control;
- typing user text into apps;
- screen-aware automation;
- file access where user data may be exposed.

Sensitive actions require clear user confirmation.

### Critical

Examples:

- passwords;
- payments;
- banking;
- purchases;
- destructive file actions;
- account or security changes;
- credentials and OTP handling.

Critical actions must be blocked or require a stronger verification flow. They must never run silently.

## Automation Permission Policy

- No arbitrary shell execution.
- No user-provided executable paths.
- No `shell=True` process launching for user commands.
- No unrestricted pyautogui access.
- No blind clicking.
- No automation on sensitive screens.
- Emergency stop or interrupt must be available for control flows.

## Voice Privacy Note

Browser push-to-talk starts only when the user clicks Talk and browser support/permission allows it.

Desktop voice runtime is disabled by default for production safety unless explicitly enabled in the local environment. AURA must not claim always-on listening unless the runtime is actually active.

## Screen Capture Privacy Note

Screen capture and OCR are used for safety/context checks. They can expose visible private information, so screen-aware actions must remain permission-gated and transparent.

## Secrets and Environment Variables

Never commit:

- `.env`;
- provider API keys;
- passwords;
- local memory databases;
- security logs;
- generated private documents.

The `.gitignore` is expected to protect common local artifacts, but contributors must still review staged files before committing.

