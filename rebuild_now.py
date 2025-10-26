#!/usr/bin/env python
"""Rebuild vector database with page numbers - no confirmation needed"""

import os
import sys

# Import the necessary components
from doc_processor import DocumentProcessor
from vector_store import VectorStore
from pathlib import Path
import json

print("=" * 70)
print("REBUILDING VECTOR DATABASE WITH PAGE NUMBERS")
print("=" * 70)

# Step 1: Process documents
print("\nStep 1: Processing documents...")
processor = DocumentProcessor()
all_chunks = []

# Process Commercial Code
commercial_code_file = "malta_commercial_code_text.txt"
if os.path.exists(commercial_code_file):
    print(f"Processing {commercial_code_file}...")
    result = processor.process_document(commercial_code_file)

    with open('processed_chunks.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    all_chunks.extend(chunks)
    print(f"  Added {len(chunks)} chunks")

# Process OCR files
ocr_output_dir = Path("ocr/output")
if ocr_output_dir.exists():
    txt_files = sorted(ocr_output_dir.glob("*.txt"))
    print(f"\nProcessing {len(txt_files)} OCR files...")

    for txt_file in txt_files:
        print(f"Processing {txt_file.name}...")
        result = processor.process_document(str(txt_file))

        with open('processed_chunks.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        all_chunks.extend(chunks)
        print(f"  Added {len(chunks)} chunks")

print(f"\nTotal chunks processed: {len(all_chunks)}")

# Step 2: Build vector database
print("\nStep 2: Building vector database...")
print("Initializing vector store (this will load all chunks)...")
vector_store = VectorStore()

print("\n" + "=" * 70)
print("REBUILD COMPLETE!")
print("=" * 70)
print(f"\nTotal documents: {len(set(c['metadata']['document'] for c in all_chunks))}")
print(f"Total chunks: {len(all_chunks)}")
print("\nPage numbers are now included in the database.")
print("\nTo test:")
print("  streamlit run main.py")
