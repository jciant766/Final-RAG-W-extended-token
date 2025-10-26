#!/usr/bin/env python
"""
Rebuild vector database with ALL documents - no discrimination
Processes all 44 documents and loads all 2436 chunks properly
"""

import os
import sys
from pathlib import Path
import json

print("=" * 80)
print("REBUILDING VECTOR DATABASE - ALL DOCUMENTS")
print("=" * 80)

# Import required components
from doc_processor import DocumentProcessor
from vector_store import VectorStore

# Initialize processor
processor = DocumentProcessor()
all_chunks = []
documents_processed = []

# Step 1: Process Commercial Code
print("\n[1/2] Processing Commercial Code...")
commercial_code_file = "malta_commercial_code_text.txt"

if os.path.exists(commercial_code_file):
    print(f"  Processing: {commercial_code_file}")
    result = processor.process_document(commercial_code_file)

    # Load chunks from the temporary file
    with open('processed_chunks.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    all_chunks.extend(chunks)
    documents_processed.append({
        'file': commercial_code_file,
        'chunks': len(chunks)
    })
    print(f"  -> Added {len(chunks)} chunks (Total so far: {len(all_chunks)})")

# Step 2: Process OCR output files
print("\n[2/2] Processing OCR output files...")
ocr_output_dir = Path("ocr/output")

if ocr_output_dir.exists():
    txt_files = sorted(ocr_output_dir.glob("*.txt"))
    print(f"  Found {len(txt_files)} files to process\n")

    for idx, txt_file in enumerate(txt_files, 1):
        print(f"  [{idx}/{len(txt_files)}] Processing: {txt_file.name}")

        try:
            result = processor.process_document(str(txt_file))

            # Load chunks from the temporary file
            with open('processed_chunks.json', 'r', encoding='utf-8') as f:
                chunks = json.load(f)

            all_chunks.extend(chunks)
            documents_processed.append({
                'file': txt_file.name,
                'chunks': len(chunks)
            })
            print(f"      -> Added {len(chunks)} chunks (Total: {len(all_chunks)})")

        except Exception as e:
            print(f"      ERROR processing {txt_file.name}: {e}")
            continue

else:
    print("  ERROR: ocr/output directory not found!")
    sys.exit(1)

# Summary of processing
print("\n" + "=" * 80)
print("DOCUMENT PROCESSING COMPLETE")
print("=" * 80)
print(f"Total documents processed: {len(documents_processed)}")
print(f"Total chunks accumulated: {len(all_chunks)}")

# Show breakdown by document
print("\nBreakdown by document:")
for doc in documents_processed[:10]:
    print(f"  - {doc['file']}: {doc['chunks']} chunks")
if len(documents_processed) > 10:
    print(f"  ... and {len(documents_processed) - 10} more documents")

# Save all chunks to the final file
print("\nSaving all chunks to processed_chunks.json...")
with open('processed_chunks.json', 'w', encoding='utf-8') as f:
    json.dump(all_chunks, f, ensure_ascii=False)
print(f"Saved {len(all_chunks)} chunks")

# Step 3: Load into vector database
print("\n" + "=" * 80)
print("LOADING INTO VECTOR DATABASE")
print("=" * 80)
print(f"Initializing VectorStore...")
print(f"This will load all {len(all_chunks)} chunks with embeddings...")
print(f"(This may take 2-3 minutes)")

try:
    vector_store = VectorStore()
    actual_count = vector_store.collection.count()

    print(f"\nVector database loaded!")
    print(f"Chunks in database: {actual_count}")

    if actual_count == len(all_chunks):
        print("\nSUCCESS: All chunks loaded correctly!")
    else:
        print(f"\nWARNING: Expected {len(all_chunks)} but got {actual_count}")

except Exception as e:
    print(f"\nERROR loading vector database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final summary
print("\n" + "=" * 80)
print("REBUILD COMPLETE")
print("=" * 80)
print(f"Documents processed: {len(documents_processed)}")
print(f"Total chunks: {len(all_chunks)}")
print(f"Chunks in vector DB: {actual_count}")
print(f"\nDatabase size:")
os.system('du -sh chroma_db 2>/dev/null || echo "Size check not available on Windows"')

print("\nYour database is ready!")
print("Test it with: streamlit run main.py")
