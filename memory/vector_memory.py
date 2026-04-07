import chromadb
import os
from datetime import datetime

# Setup ChromaDB
client = chromadb.PersistentClient(path="memory/vector_store")
collection = client.get_or_create_collection(name="aura_memory")

def store_memory(text, metadata=None):
    if metadata is None:
        metadata = {}
    metadata["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    collection.add(
        documents=[text],
        metadatas=[metadata],
        ids=[f"mem_{datetime.now().timestamp()}"]
    )

def search_memory(query, n_results=3):
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        if results and results['documents']:
            return results['documents'][0]
        return []
    except:
        return []

def get_all_memories():
    try:
        results = collection.get()
        return results['documents']
    except:
        return []