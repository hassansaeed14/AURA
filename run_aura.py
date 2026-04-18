from __future__ import annotations

import json
import os
import socket
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from a2wsgi import ASGIMiddleware
from waitress import serve

from api.api_server import app as fastapi_app


# ───────────────────────────────────────────────────
# PATHS
# ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
SERVER_CONFIG_PATH = CONFIG_DIR / "server.json"


# ───────────────────────────────────────────────────
# DEFAULT CONFIG
# ───────────────────────────────────────────────────
DEFAULT_SERVER_CONFIG: dict[str, Any] = {
    "host": "0.0.0.0",
    "port": 5000,
    "workers": 4,
    "debug": False,
    "auto_open_browser": True,
}


# ───────────────────────────────────────────────────
# CONFIG LOADER
# ───────────────────────────────────────────────────
def load_server_config() -> dict[str, Any]:
    if not SERVER_CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SERVER_CONFIG_PATH.write_text(
            json.dumps(DEFAULT_SERVER_CONFIG, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_SERVER_CONFIG)

    try:
        data = json.loads(SERVER_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            config = dict(DEFAULT_SERVER_CONFIG)
            config.update(data)
            return config
    except Exception:
        pass

    return dict(DEFAULT_SERVER_CONFIG)


# ───────────────────────────────────────────────────
# UTILITIES
# ───────────────────────────────────────────────────
def build_url(host: str, port: int) -> str:
    if host in {"0.0.0.0", "::"}:
        host = "localhost"
    return f"http://{host}:{port}"


def wait_for_server(host: str, port: int, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host

    while time.time() < deadline:
        try:
            with socket.create_connection((probe_host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)

    return False


def open_browser(url: str, host: str, port: int) -> None:
    if wait_for_server(host, port):
        try:
            webbrowser.open(url)
        except Exception:
            pass


# ───────────────────────────────────────────────────
# BOOT UI
# ───────────────────────────────────────────────────
def print_boot_banner(url: str, config: dict[str, Any]) -> None:
    print("\n" + "═" * 55)
    print(" AURA — Autonomous Universal Responsive Assistant")
    print("═" * 55)

    print("\n[System Status]")
    print("• Runtime       : FastAPI + Waitress")
    print("• Mode          : Local Private Runtime")
    print(f"• Workers       : {config.get('workers')}")
    print(f"• URL           : {url}")

    print("\n[Status]")
    print("• Boot          : OK")
    print("• API           : READY")
    print("• Interface     : AVAILABLE")

    print("\nAURA is online.\n")


# ───────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────
def main() -> None:
    config = load_server_config()

    host = str(config.get("host"))
    port = int(config.get("port"))
    threads = int(config.get("workers"))
    auto_open = bool(config.get("auto_open_browser"))

    url = build_url(host, port)

    print_boot_banner(url, config)

    # Start browser thread
    if auto_open:
        threading.Thread(
            target=open_browser,
            args=(url, host, port),
            daemon=True,
        ).start()

    # Run server
    try:
        aura_app = ASGIMiddleware(fastapi_app)
        serve(aura_app, host=host, port=port, threads=threads)

    except KeyboardInterrupt:
        print("\n[Shutdown] AURA stopped manually.")

    except Exception as e:
        print("\n[CRITICAL ERROR]")
        print(f"{e}")


# ───────────────────────────────────────────────────
if __name__ == "__main__":
    main()