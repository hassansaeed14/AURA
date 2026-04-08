import chromadb
from datetime import datetime


DB_PATH = "memory/vector_store"
COLLECTION_NAME = "aura_memory"

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def _generate_memory_id():
    return f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def store_memory(text, metadata=None):
    if not text or not str(text).strip():
        return False

    safe_metadata = metadata.copy() if metadata else {}
    safe_metadata["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        collection.add(
            documents=[str(text).strip()],
            metadatas=[safe_metadata],
            ids=[_generate_memory_id()]
        )
        return True
    except Exception as e:
        print(f"[Vector Memory Store Error] {e}")
        return False


def search_memory(query, n_results=3):
    if not query or not str(query).strip():
        return []

    try:
        results = collection.query(
            query_texts=[str(query).strip()],
            n_results=n_results
        )

        documents = results.get("documents", [[]])
        metadatas = results.get("metadatas", [[]])
        ids = results.get("ids", [[]])

        if not documents or not documents[0]:
            return []

        memories = []
        for i, doc in enumerate(documents[0]):
            memory_item = {
                "id": ids[0][i] if ids and ids[0] and i < len(ids[0]) else None,
                "text": doc,
                "metadata": metadatas[0][i] if metadatas and metadatas[0] and i < len(metadatas[0]) else {}
            }
            memories.append(memory_item)

        return memories

    except Exception as e:
        print(f"[Vector Memory Search Error] {e}")
        return []


def get_all_memories():
    try:
        results = collection.get()

        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])

        memories = []
        for i, doc in enumerate(documents):
            memory_item = {
                "id": ids[i] if i < len(ids) else None,
                "text": doc,
                "metadata": metadatas[i] if i < len(metadatas) else {}
            }
            memories.append(memory_item)

        return memories

    except Exception as e:
        print(f"[Vector Memory Get All Error] {e}")
        return []


def delete_memory(memory_id):
    if not memory_id:
        return False

    try:
        collection.delete(ids=[memory_id])
        return True
    except Exception as e:
        print(f"[Vector Memory Delete Error] {e}")
        return False


def clear_all_memories():
    global collection

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return True