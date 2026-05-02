from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


MIN_OCR_CONFIDENCE = 35.0
BUTTON_KEYWORDS = {
    "ok",
    "cancel",
    "submit",
    "send",
    "save",
    "open",
    "close",
    "next",
    "back",
    "continue",
    "search",
    "go",
}
INPUT_KEYWORDS = {
    "search",
    "type",
    "enter",
    "name",
    "email",
    "message",
    "query",
    "find",
    "url",
    "address",
}
SENSITIVE_SCREEN_KEYWORDS = {
    "bank",
    "banking",
    "payment",
    "checkout",
    "password",
    "otp",
    "login",
    "sign in",
    "credit card",
    "credentials",
}


@dataclass
class OCRItem:
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        x, y, width, height = self.bbox
        return {
            "text": self.text,
            "bbox": {"x": x, "y": y, "width": width, "height": height},
            "confidence": self.confidence,
        }


@dataclass
class UIElement:
    kind: str
    label: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        x, y, width, height = self.bbox
        return {
            "kind": self.kind,
            "label": self.label,
            "bbox": {"x": x, "y": y, "width": width, "height": height},
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class ScreenObservation:
    success: bool
    status: str
    message: str
    size: Tuple[int, int] = (0, 0)
    visible_text: str = ""
    ocr_items: List[OCRItem] = field(default_factory=list)
    ui_elements: List[UIElement] = field(default_factory=list)
    sensitive_detected: bool = False
    candidate_element: Optional[UIElement] = None
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "size": {"width": self.size[0], "height": self.size[1]},
            "visible_text": self.visible_text,
            "ocr_items": [item.to_dict() for item in self.ocr_items],
            "ui_elements": [item.to_dict() for item in self.ui_elements],
            "sensitive_detected": self.sensitive_detected,
            "candidate_element": self.candidate_element.to_dict() if self.candidate_element else None,
            "error": self.error,
        }


def _safe_error(message: str, error: Exception | str) -> ScreenObservation:
    return ScreenObservation(
        success=False,
        status="unavailable",
        message=message,
        error=str(error),
    )


def capture_screen_image():
    """Capture one screenshot and return a PIL image object.

    This is intentionally a one-shot capture. There is no continuous screen
    watching and no click/keyboard control here.
    """

    try:
        import pyautogui  # type: ignore

        pyautogui.FAILSAFE = True
        return pyautogui.screenshot()
    except Exception:
        from PIL import ImageGrab  # type: ignore

        return ImageGrab.grab()


def capture_screenshot() -> Dict[str, Any]:
    try:
        image = capture_screen_image()
        width, height = image.size
        return {
            "success": True,
            "status": "captured",
            "message": "Screenshot captured.",
            "image": image,
            "size": {"width": width, "height": height},
        }
    except Exception as error:
        return _safe_error("Screen capture is unavailable.", error).to_dict()


def _parse_confidence(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def extract_ocr(image: Any) -> Dict[str, Any]:
    try:
        import pytesseract  # type: ignore
    except Exception as error:
        return _safe_error("OCR is unavailable because pytesseract could not load.", error).to_dict()

    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        items: List[OCRItem] = []
        count = len(data.get("text", []))
        for index in range(count):
            text = str(data.get("text", [""])[index] or "").strip()
            confidence = _parse_confidence(data.get("conf", ["-1"])[index])
            if not text or confidence < MIN_OCR_CONFIDENCE:
                continue
            item = OCRItem(
                text=text,
                bbox=(
                    int(data.get("left", [0])[index] or 0),
                    int(data.get("top", [0])[index] or 0),
                    int(data.get("width", [0])[index] or 0),
                    int(data.get("height", [0])[index] or 0),
                ),
                confidence=confidence,
            )
            items.append(item)
        visible_text = " ".join(item.text for item in items).strip()
        return {
            "success": True,
            "status": "ocr_complete",
            "message": "OCR completed.",
            "visible_text": visible_text,
            "ocr_items": [item.to_dict() for item in items],
        }
    except Exception as error:
        return _safe_error("OCR failed for the captured screen.", error).to_dict()


def _bbox_from_item(item: Dict[str, Any]) -> Tuple[int, int, int, int]:
    bbox = item.get("bbox") if isinstance(item.get("bbox"), dict) else {}
    return (
        int(bbox.get("x") or 0),
        int(bbox.get("y") or 0),
        int(bbox.get("width") or 0),
        int(bbox.get("height") or 0),
    )


def _item_text(item: Dict[str, Any]) -> str:
    return str(item.get("text") or "").strip()


def _item_confidence(item: Dict[str, Any]) -> float:
    return _parse_confidence(item.get("confidence"))


def _label_matches(label: str, keywords: Iterable[str]) -> bool:
    lowered = label.lower()
    return any(keyword in lowered for keyword in keywords)


def detect_sensitive_screen_text(visible_text: str | None) -> bool:
    return _label_matches(str(visible_text or ""), SENSITIVE_SCREEN_KEYWORDS)


def detect_ui_elements(ocr_items: List[Dict[str, Any]], image_size: Tuple[int, int] | None = None) -> List[Dict[str, Any]]:
    elements: List[UIElement] = []
    for item in ocr_items:
        label = _item_text(item)
        if not label:
            continue
        bbox = _bbox_from_item(item)
        confidence = _item_confidence(item)
        lowered = label.lower()
        width = bbox[2]
        height = bbox[3]

        if _label_matches(lowered, BUTTON_KEYWORDS) and len(label) <= 24:
            elements.append(UIElement("button", label, bbox, confidence, "button-like OCR label"))

        if _label_matches(lowered, INPUT_KEYWORDS):
            kind = "search_bar" if "search" in lowered or "find" in lowered else "input_field"
            elements.append(UIElement(kind, label, bbox, confidence, "input/search label"))

        if width > 180 and height <= 48 and len(label) >= 8:
            elements.append(UIElement("input_field", label, bbox, max(confidence, 45.0), "wide text-heavy area"))

    if image_size and not elements:
        width, height = image_size
        if width and height:
            elements.append(
                UIElement(
                    "input_field",
                    "active app editing area",
                    (int(width * 0.08), int(height * 0.18), int(width * 0.84), int(height * 0.7)),
                    35.0,
                    "fallback editable region estimate",
                )
            )

    deduped: List[UIElement] = []
    seen = set()
    for element in elements:
        key = (element.kind, element.label.lower(), element.bbox)
        if key in seen:
            continue
        deduped.append(element)
        seen.add(key)
    return [element.to_dict() for element in deduped]


def observe_screen() -> Dict[str, Any]:
    capture = capture_screenshot()
    if not capture.get("success"):
        return capture

    image = capture.get("image")
    size_payload = capture.get("size") if isinstance(capture.get("size"), dict) else {}
    image_size = (int(size_payload.get("width") or 0), int(size_payload.get("height") or 0))
    ocr = extract_ocr(image)
    if not ocr.get("success"):
        observation = ScreenObservation(
            success=False,
            status=str(ocr.get("status") or "ocr_unavailable"),
            message=str(ocr.get("message") or "OCR unavailable."),
            size=image_size,
            error=str(ocr.get("error") or ""),
        )
        return observation.to_dict()

    ocr_items = [item for item in ocr.get("ocr_items", []) if isinstance(item, dict)]
    visible_text = str(ocr.get("visible_text") or "")
    ui_elements = detect_ui_elements(ocr_items, image_size)
    candidate = next(
        (
            element
            for element in ui_elements
            if element.get("kind") in {"search_bar", "input_field"}
        ),
        None,
    )
    observation = ScreenObservation(
        success=True,
        status="observed",
        message="Screen observed with OCR.",
        size=image_size,
        visible_text=visible_text,
        ocr_items=[
            OCRItem(_item_text(item), _bbox_from_item(item), _item_confidence(item))
            for item in ocr_items
        ],
        ui_elements=[
            UIElement(
                str(element.get("kind") or ""),
                str(element.get("label") or ""),
                _bbox_from_item(element),
                _item_confidence(element),
                str(element.get("reason") or ""),
            )
            for element in ui_elements
        ],
        sensitive_detected=detect_sensitive_screen_text(visible_text),
        candidate_element=(
            UIElement(
                str(candidate.get("kind") or ""),
                str(candidate.get("label") or ""),
                _bbox_from_item(candidate),
                _item_confidence(candidate),
                str(candidate.get("reason") or ""),
            )
            if candidate
            else None
        ),
    )
    return observation.to_dict()


def screen_context_for_automation(target_app: str | None, action_type: str) -> Dict[str, Any]:
    observation = observe_screen()
    if not observation.get("success"):
        observation["target_app"] = target_app
        observation["action_type"] = action_type
        observation["candidate_required"] = False
        return observation

    candidate = observation.get("candidate_element")
    if not candidate and str(target_app or "").lower() in {"notepad", "vs code"} and action_type == "type_text":
        width = int((observation.get("size") or {}).get("width") or 0)
        height = int((observation.get("size") or {}).get("height") or 0)
        candidate = {
            "kind": "input_field",
            "label": "active editor area",
            "bbox": {"x": int(width * 0.05), "y": int(height * 0.12), "width": int(width * 0.9), "height": int(height * 0.78)},
            "confidence": 40.0,
            "reason": "supported editor app active",
        }
        observation["candidate_element"] = candidate
        observation.setdefault("ui_elements", []).append(candidate)

    observation["target_app"] = target_app
    observation["action_type"] = action_type
    observation["candidate_required"] = action_type == "type_text"
    observation["confirmation_required"] = True
    return observation


__all__ = [
    "capture_screen_image",
    "capture_screenshot",
    "detect_sensitive_screen_text",
    "detect_ui_elements",
    "extract_ocr",
    "observe_screen",
    "screen_context_for_automation",
]
