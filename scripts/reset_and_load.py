#!/usr/bin/env python3
import shutil
import os
import chromadb
from chromadb.config import Settings
from vector_store import VectorStore

def main():
    print("Resetting and loading chunks into vector database from processed_chunks.json ...")
    
    try:
        # Ensure the canonical processed file exists; prefer existing processed_chunks.json
        if not os.path.exists('processed_chunks.json'):
            # Fallback to fixed set if available
            if os.path.exists('all_processed_chunks_fixed.json'):
                shutil.copy('all_processed_chunks_fixed.json', 'processed_chunks.json')
                print("Seeded from all_processed_chunks_fixed.json")
            elif os.path.exists('all_processed_chunks.json'):
                shutil.copy('all_processed_chunks.json', 'processed_chunks.json')
                print("Seeded from all_processed_chunks.json")
            else:
                print("No processed chunks file found.")
                return False
        else:
            print("Using existing processed_chunks.json")
        
        # Delete existing collection
        client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        try:
            client.delete_collection("malta_code_v2")
            print("Deleted existing collection")
        except:
            print("No existing collection to delete")
        
        # Initialize vector store (this will create new collection and load chunks)
        vector_store = VectorStore()
        print("Vector store initialized and chunks loaded")
        
        # Get some stats
        collection = vector_store.collection
        count = collection.count()
        print(f"Total documents in database: {count}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n✓ Successfully loaded all chunks into vector database!")
        print("✓ Ready to launch Streamlit!")
    else:
        print("\n✗ Failed to load chunks into vector database")
