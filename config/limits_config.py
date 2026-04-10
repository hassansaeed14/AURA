from __future__ import annotations

from typing import Dict


MAX_MULTI_COMMANDS = 5
MAX_PLAN_STEPS = 8
MAX_TOOL_TIMEOUT_SECONDS = 20
MAX_FILE_BYTES = 2_000_000
MAX_TEXT_INPUT_CHARS = 6_000
MAX_HISTORY_SEARCH_RESULTS = 25


def get_runtime_limits() -> Dict[str, int]:
    return {
        "max_multi_commands": MAX_MULTI_COMMANDS,
        "max_plan_steps": MAX_PLAN_STEPS,
        "max_tool_timeout_seconds": MAX_TOOL_TIMEOUT_SECONDS,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_text_input_chars": MAX_TEXT_INPUT_CHARS,
        "max_history_search_results": MAX_HISTORY_SEARCH_RESULTS,
    }
