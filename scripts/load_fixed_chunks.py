#!/usr/bin/env python3
import shutil
import chromadb
from chromadb.config import Settings
from vector_store import VectorStore

def main():
    print("Loading fixed chunks into vector database...")
    
    try:
        # Copy our fixed chunks to the expected filename
        shutil.copy('all_processed_chunks_fixed.json', 'processed_chunks.json')
        print("✓ Copied fixed chunks to processed_chunks.json")
        
        # Delete existing collection
        client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        try:
            client.delete_collection("malta_code_v2")
            print("✓ Deleted existing collection")
        except:
            print("✓ No existing collection to delete")
        
        # Initialize vector store (this will create new collection and load chunks)
        vector_store = VectorStore()
        print("✓ Vector store initialized and chunks loaded")
        
        # Get some stats
        collection = vector_store.collection
        count = collection.count()
        print(f"✓ Total documents in database: {count}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n✓ Successfully loaded all chunks into vector database!")
        print("✓ Ready to launch Streamlit!")
    else:
        print("\n✗ Failed to load chunks into vector database")

