#!/usr/bin/env python3
import shutil
from vector_store import VectorStore

def main():
    print("Loading all chunks into vector database...")
    
    try:
        # Copy our processed chunks to the expected filename
        shutil.copy('all_processed_chunks.json', 'processed_chunks.json')
        print("✓ Copied chunks to processed_chunks.json")
        
        # Initialize vector store (this will automatically load the chunks)
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

