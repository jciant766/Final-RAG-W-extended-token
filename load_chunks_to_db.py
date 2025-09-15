#!/usr/bin/env python3
import json
from vector_store import VectorStore

def load_chunks_to_vector_db():
    """Load chunks from all_processed_chunks.json into ChromaDB"""
    print("Loading chunks into vector database...")
    
    try:
        # Load chunks from JSON file
        with open('all_processed_chunks.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        print(f"Loaded {len(chunks)} chunks from JSON file")
        
        # Initialize vector store
        vector_store = VectorStore()
        
        # Clear existing collection by recreating it
        try:
            vector_store.collection.delete()
        except:
            # If delete fails, try to get all and delete them
            try:
                all_docs = vector_store.collection.get()
                if all_docs['ids']:
                    vector_store.collection.delete(ids=all_docs['ids'])
            except:
                pass  # Continue anyway
        
        print("✓ Cleared existing collection")
        
        # Load new chunks
        vector_store.load_documents(chunks)
        print(f"✓ Loaded {len(chunks)} chunks into vector database")
        
        return True
    except Exception as e:
        print(f"✗ Error loading into vector database: {e}")
        return False

if __name__ == "__main__":
    if load_chunks_to_vector_db():
        print("\n✓ Successfully loaded all chunks into vector database!")
        print("✓ Ready to launch Streamlit!")
    else:
        print("\n✗ Failed to load chunks into vector database")

