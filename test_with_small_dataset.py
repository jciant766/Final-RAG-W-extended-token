#!/usr/bin/env python3
"""
Test with minimal data to verify system works before processing all 1,069 chunks
"""

import json
from vector_store import VectorStore
from search_engine import SearchEngine

# Load just first 10 chunks for testing
with open('processed_chunks.json', 'r', encoding='utf-8') as f:
    all_chunks = json.load(f)

print(f"Total chunks available: {len(all_chunks)}")
print("Creating test set with first 10 chunks...")

# Save test set
test_chunks = all_chunks[:10]
with open('test_chunks.json', 'w', encoding='utf-8') as f:
    json.dump(test_chunks, f, ensure_ascii=False, indent=2)

print(f"Test set created: {len(test_chunks)} chunks")
print("\nTo test:")
print("1. Temporarily rename processed_chunks.json to processed_chunks_full.json")
print("2. Rename test_chunks.json to processed_chunks.json")
print("3. Delete chroma_db folder")
print("4. Run streamlit")
print("5. When done, restore original files")


