#!/usr/bin/env python3
import shutil
import os
import time
import chromadb
from chromadb.config import Settings
from vector_store import VectorStore

def force_reset():
    print("Force resetting ChromaDB...")
    
    try:
        # Try to delete collection first
        client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        try:
            client.delete_collection("malta_code_v2")
            print("Deleted existing collection")
        except Exception as e:
            print(f"Collection deletion failed: {e}")
        
        # Wait a moment
        time.sleep(1)
        
        # Force delete directory if it exists
        if os.path.exists("chroma_db"):
            try:
                shutil.rmtree("chroma_db", ignore_errors=True)
                print("Removed chroma_db directory")
            except Exception as e:
                print(f"Directory removal failed: {e}")
        
        # Wait for file handles to release
        time.sleep(2)
        
        # Rebuild from scratch
        print("Rebuilding vector store...")
        vector_store = VectorStore()
        
        # Get stats
        collection = vector_store.collection
        count = collection.count()
        print(f"Total documents in database: {count}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if force_reset():
        print("Successfully reset and rebuilt database!")
    else:
        print("Failed to reset database")

