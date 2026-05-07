import os
import chromadb
from chromadb.config import Settings

CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chroma_db")
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR, settings=Settings(anonymized_telemetry=False))

def get_chroma_collection():
    return chroma_client.get_or_create_collection(
        name="aura_knowledge_base",
        metadata={"hnsw:space": "cosine"}
    )
