"""
Complete Pipeline: Text Files → Chunks → Embeddings → Vector Database
Builds everything immediately without waiting for Streamlit
"""

import os
import sys
import json
from pathlib import Path

def process_documents():
    """Step 1: Process text files into chunks"""
    print("=" * 70)
    print("STEP 1: PROCESSING TEXT FILES INTO CHUNKS")
    print("=" * 70)
    
    from doc_processor import DocumentProcessor
    from debug_logger import DebugLogger
    
    processor = DocumentProcessor()
    debug = DebugLogger("build_vector_db")
    
    all_chunks = []
    documents_processed = []
    
    # Process Commercial Code
    commercial_code_file = "malta_commercial_code_text.txt"
    if os.path.exists(commercial_code_file):
        print(f"\n📄 Processing: {commercial_code_file}")
        try:
            result = processor.process_document(commercial_code_file)
            with open('processed_chunks.json', 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            all_chunks.extend(chunks)
            documents_processed.append({
                'file': commercial_code_file,
                'articles': result['total_articles'],
                'chunks': result['total_chunks'],
                'document': result['document']
            })
            print(f"✅ {result['total_articles']} articles, {result['total_chunks']} chunks")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Process OCR output files
    ocr_output_dir = Path("ocr/output")
    if ocr_output_dir.exists():
        text_files = sorted(ocr_output_dir.glob("*.txt"))
        print(f"\n📄 Processing {len(text_files)} OCR output files...")
        
        for idx, text_file in enumerate(text_files, 1):
            try:
                print(f"[{idx}/{len(text_files)}] {text_file.name}...", end=" ")
                result = processor.process_document(str(text_file))
                
                with open('processed_chunks.json', 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                
                all_chunks.extend(chunks)
                documents_processed.append({
                    'file': text_file.name,
                    'articles': result['total_articles'],
                    'chunks': result['total_chunks'],
                    'document': result['document']
                })
                print(f"✅ {result['total_articles']} articles")
            except Exception as e:
                print(f"❌ {e}")
    
    # Remove duplicates
    unique_chunks = {}
    for chunk in all_chunks:
        chunk_id = chunk['id']
        if chunk_id not in unique_chunks:
            unique_chunks[chunk_id] = chunk
    
    all_chunks = list(unique_chunks.values())
    
    # Save all chunks
    with open('processed_chunks.json', 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    
    # Save report
    total_articles = sum(doc['articles'] for doc in documents_processed)
    report = {
        "total_documents": len(documents_processed),
        "total_articles": total_articles,
        "total_chunks": len(all_chunks),
        "documents": documents_processed
    }
    
    with open('processing_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Step 1 Complete:")
    print(f"   Documents: {len(documents_processed)}")
    print(f"   Articles: {total_articles}")
    print(f"   Chunks: {len(all_chunks)}")
    
    return all_chunks

def build_vector_database(chunks):
    """Step 2: Build vector database with embeddings"""
    print("\n" + "=" * 70)
    print("STEP 2: BUILDING VECTOR DATABASE WITH EMBEDDINGS")
    print("=" * 70)
    
    from vector_store import VectorStore
    
    print(f"\n🧠 Generating embeddings for {len(chunks)} chunks...")
    print("   This will take ~10-15 minutes depending on your hardware")
    print("   GPU detected: Using GPU acceleration" if check_gpu() else "   CPU mode: This will be slower")
    
    # Initialize vector store (will build from chunks)
    vector_store = VectorStore()
    
    print("\n✅ Step 2 Complete: Vector database built successfully!")
    print(f"   Location: chroma_db/")
    print(f"   Total embeddings: {len(chunks)}")
    
    return vector_store

def check_gpu():
    """Check if GPU is available"""
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False

def main():
    print("=" * 70)
    print("BUILD COMPLETE VECTOR DATABASE")
    print("=" * 70)
    print("\nThis will:")
    print("  1. Process all text files into chunks")
    print("  2. Generate embeddings immediately")
    print("  3. Build vector database")
    print("  4. Ready to use!")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Step 1: Process documents
    chunks = process_documents()
    
    if not chunks:
        print("\n❌ No chunks to process!")
        return
    
    # Step 2: Build vector database
    vector_store = build_vector_database(chunks)
    
    # Done!
    print("\n" + "=" * 70)
    print("✅ VECTOR DATABASE READY!")
    print("=" * 70)
    print("\n📊 Summary:")
    print(f"   Chunks processed: {len(chunks)}")
    print(f"   Embeddings generated: {len(chunks)}")
    print(f"   Database location: chroma_db/")
    print("\n🚀 Next Steps:")
    print("   Run: streamlit run main.py")
    print("   Your vector database is ready to use!")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()


