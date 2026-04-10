from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None


DB_PATH = Path("memory/vector_store")
COLLECTION_NAME = "aura_memory"
FALLBACK_FILE = Path("memory/vector_store_fallback.json")

client = None
collection = None
backend = "uninitialized"
last_error = None


def _set_backend(mode: str, error: Exception | str | None = None) -> None:
    global backend, last_error
    backend = mode
    last_error = str(error) if error else None


def _generate_memory_id() -> str:
    return f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def _init_vector_store() -> bool:
    global client, collection

    if collection is not None:
        _set_backend("vector")
        return True

    if chromadb is None:
        _set_backend("fallback", "chromadb unavailable")
        return False

    try:
        DB_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(DB_PATH))
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        _set_backend("vector")
        return True
    except Exception as error:
        client = None
        collection = None
        _set_backend("fallback", error)
        return False


def _fallback_read() -> List[Dict[str, Any]]:
    if not FALLBACK_FILE.exists():
        return []
    try:
        payload = json.loads(FALLBACK_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _fallback_write(items: List[Dict[str, Any]]) -> bool:
    try:
        FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        FALLBACK_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def _merge_memories(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen_ids = set()
    for group in groups:
        for item in group:
            memory_id = item.get("id")
            dedupe_key = memory_id if memory_id else f"{item.get('text', '')}|{item.get('metadata', {})}"
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            merged.append(item)
    return merged


def _normalize_memory_item(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata", {})
    return {
        "id": item.get("id"),
        "text": str(item.get("text", "")),
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


def _fallback_store(text: str, metadata: Dict[str, Any]) -> bool:
    items = _fallback_read()
    items.append(
        {
            "id": _generate_memory_id(),
            "text": text,
            "metadata": metadata,
        }
    )
    return _fallback_write(items)


def _fallback_search(query: str, n_results: int) -> List[Dict[str, Any]]:
    needle = str(query or "").strip().lower()
    if not needle:
        return []

    matches = []
    for item in reversed(_fallback_read()):
        normalized = _normalize_memory_item(item)
        haystack = " ".join(
            [
                normalized["text"],
                " ".join(f"{key}:{value}" for key, value in normalized["metadata"].items()),
            ]
        ).lower()
        if needle in haystack:
            matches.append(normalized)
        if len(matches) >= max(1, int(n_results)):
            break
    return matches


def _fallback_delete(memory_id: str) -> bool:
    items = _fallback_read()
    updated = [item for item in items if item.get("id") != memory_id]
    if len(updated) == len(items):
        return False
    return _fallback_write(updated)


def _fallback_clear() -> bool:
    return _fallback_write([])


def get_status() -> Dict[str, Any]:
    current_backend = "vector" if collection is not None else backend
    if current_backend == "uninitialized":
        _init_vector_store()
        current_backend = "vector" if collection is not None else backend

    return {
        "backend": current_backend,
        "vector_store_ready": collection is not None,
        "fallback_file": str(FALLBACK_FILE),
        "last_error": last_error,
    }


def store_memory(text, metadata=None):
    global client, collection

    normalized_text = str(text or "").strip()
    if not normalized_text:
        return False

    safe_metadata = metadata.copy() if isinstance(metadata, dict) else {}
    safe_metadata["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if _init_vector_store():
        try:
            collection.add(
                documents=[normalized_text],
                metadatas=[safe_metadata],
                ids=[_generate_memory_id()]
            )
            return True
        except Exception as error:
            client = None
            collection = None
            _set_backend("fallback", error)

    return _fallback_store(normalized_text, safe_metadata)


def search_memory(query, n_results=3):
    global client, collection

    normalized_query = str(query or "").strip()
    if not normalized_query:
        return []

    vector_results: List[Dict[str, Any]] = []
    if _init_vector_store():
        try:
            results = collection.query(
                query_texts=[normalized_query],
                n_results=n_results
            )

            documents = results.get("documents", [[]])
            metadatas = results.get("metadatas", [[]])
            ids = results.get("ids", [[]])

            if documents and documents[0]:
                for i, doc in enumerate(documents[0]):
                    vector_results.append(
                        {
                            "id": ids[0][i] if ids and ids[0] and i < len(ids[0]) else None,
                            "text": doc,
                            "metadata": metadatas[0][i] if metadatas and metadatas[0] and i < len(metadatas[0]) else {},
                        }
                    )
        except Exception as error:
            client = None
            collection = None
            _set_backend("fallback", error)
            vector_results = []

    fallback_results = _fallback_search(normalized_query, n_results)
    return _merge_memories(vector_results, fallback_results)[: max(1, int(n_results))]


def get_all_memories():
    global client, collection

    vector_results: List[Dict[str, Any]] = []
    if _init_vector_store():
        try:
            results = collection.get()

            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            ids = results.get("ids", [])

            for i, doc in enumerate(documents):
                vector_results.append(
                    {
                        "id": ids[i] if i < len(ids) else None,
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                    }
                )
        except Exception as error:
            client = None
            collection = None
            _set_backend("fallback", error)
            vector_results = []

    fallback_results = [_normalize_memory_item(item) for item in _fallback_read()]
    return _merge_memories(vector_results, fallback_results)


def delete_memory(memory_id):
    global client, collection

    normalized_id = str(memory_id or "").strip()
    if not normalized_id:
        return False

    deleted = _fallback_delete(normalized_id)

    if _init_vector_store():
        try:
            collection.delete(ids=[normalized_id])
            return True
        except Exception as error:
            client = None
            collection = None
            _set_backend("fallback", error)

    return deleted


def clear_all_memories():
    global client, collection

    cleared = _fallback_clear()

    if _init_vector_store() and client is not None:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        try:
            collection = client.get_or_create_collection(name=COLLECTION_NAME)
            _set_backend("vector")
            return True
        except Exception as error:
            client = None
            collection = None
            _set_backend("fallback", error)

    return cleared


_init_vector_store()
