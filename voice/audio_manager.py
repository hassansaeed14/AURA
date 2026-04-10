from __future__ import annotations

from typing import Any, Dict, List

try:
    import sounddevice as sd  # type: ignore
except Exception:  # pragma: no cover
    sd = None


def audio_backend_available() -> bool:
    return sd is not None


def list_audio_devices() -> List[Dict[str, Any]]:
    if sd is None:
        return []
    devices = []
    for index, device in enumerate(sd.query_devices()):  # type: ignore[arg-type]
        devices.append(
            {
                "index": index,
                "name": device.get("name"),
                "max_input_channels": device.get("max_input_channels"),
                "max_output_channels": device.get("max_output_channels"),
                "default_samplerate": device.get("default_samplerate"),
            }
        )
    return devices


def get_audio_status() -> Dict[str, Any]:
    devices = list_audio_devices()
    return {
        "available": audio_backend_available(),
        "backend": "sounddevice" if audio_backend_available() else "unavailable",
        "device_count": len(devices),
        "devices": devices[:8],
    }
