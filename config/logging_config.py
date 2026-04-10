from __future__ import annotations

from pathlib import Path
from typing import Dict


LOG_DIR = Path("memory") / "logs"
APP_LOG_FILE = LOG_DIR / "aura.log"
SECURITY_LOG_FILE = LOG_DIR / "security.log"
AUDIT_LOG_FILE = LOG_DIR / "audit.log"

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logging_defaults() -> Dict[str, str]:
    return {
        "log_level": DEFAULT_LOG_LEVEL,
        "log_format": DEFAULT_LOG_FORMAT,
        "app_log_file": str(APP_LOG_FILE),
        "security_log_file": str(SECURITY_LOG_FILE),
        "audit_log_file": str(AUDIT_LOG_FILE),
    }
