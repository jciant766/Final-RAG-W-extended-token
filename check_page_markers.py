"""
Check which documents have page markers
Shows which source files need page markers added
"""

import os
import re
import json

print("=" * 80)
print("PAGE MARKER STATUS CHECK")
print("=" * 80)

# Check all .txt files in current directory
txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and os.path.isfile(f)]

print(f"\nFound {len(txt_files)} .txt files in current directory\n")

results = []

for file in sorted(txt_files):
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Count page markers
        markers = re.findall(r'---\s*PAGE\s*(\d+)\s*---', content, re.IGNORECASE)

        # Get file size
        size_kb = len(content) / 1024

        results.append({
            'file': file,
            'markers': len(markers),
            'size_kb': size_kb,
            'has_markers': len(markers) > 0
        })

    except Exception as e:
        print(f"Error reading {file}: {e}")

# Display results
print("FILES WITH PAGE MARKERS:")
print("-" * 80)
for r in results:
    if r['has_markers']:
        print(f"[OK] {r['file']}")
        print(f"     {r['markers']} page markers, {r['size_kb']:.1f} KB")
        print()

print("\nFILES WITHOUT PAGE MARKERS (showing Page 1 for everything):")
print("-" * 80)
for r in results:
    if not r['has_markers']:
        print(f"[MISSING] {r['file']}")
        print(f"          {r['size_kb']:.1f} KB - needs page markers added")
        print()

# Summary
with_markers = sum(1 for r in results if r['has_markers'])
without_markers = sum(1 for r in results if not r['has_markers'])

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Files WITH page markers: {with_markers}")
print(f"Files WITHOUT page markers: {without_markers}")

if without_markers > 0:
    print(f"\n{without_markers} files need page markers to show accurate page numbers.")
    print("\nTo add page markers:")
    print("1. If you have original PDFs, use `add_page_markers_to_ocr.py`")
    print("2. If text only, manually add '--- PAGE X ---' markers at page breaks")
    print("3. After adding markers, run: python build_vector_db.py")

# Check what's in the vector database
print("\n" + "=" * 80)
print("CURRENT VECTOR DATABASE STATUS")
print("=" * 80)

try:
    with open('document_metadata.json', 'r') as f:
        metadata = json.load(f)

    docs_in_db = metadata.get('documents_in_db', {})
    print(f"\nDocuments in vector database: {len(docs_in_db)}")
    print("\nSample page numbers from vector DB:")

    # Check actual page numbers in vector store
    from vector_store import VectorStore
    v = VectorStore()

    # Get sample from different documents
    results = v.search('Malta law', n_results=30)

    doc_pages = {}
    for r in results:
        doc = r['metadata'].get('document')
        page = r['metadata'].get('page')
        if doc not in doc_pages:
            doc_pages[doc] = set()
        doc_pages[doc].add(page)

    for doc, pages in sorted(doc_pages.items())[:10]:
        unique_pages = sorted(pages)
        if len(unique_pages) == 1 and unique_pages[0] == 1:
            status = "[NEEDS MARKERS]"
        else:
            status = "[HAS MARKERS]"
        print(f"{status} {doc}")
        print(f"          Pages: {unique_pages[:5]}")

except Exception as e:
    print(f"Could not check vector database: {e}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

if without_markers > 0:
    print("""
Your page numbers ARE being displayed in the Streamlit UI.
The issue is that most documents default to "Page 1" because they lack page markers.

TO FIX:
1. Add page markers to your source .txt files:
   - Format: "--- PAGE 1 ---", "--- PAGE 2 ---", etc.
   - Place at actual page breaks in the document

2. Rebuild the vector database:
   python delete_vector_db.py
   python build_vector_db.py

3. Page numbers will then show correctly in the UI

ALTERNATIVE:
If exact page numbers aren't critical, you can leave it as-is.
The system works fine with all documents showing "Page 1".
""")
else:
    print("\nAll source files have page markers!")
    print("If you're still seeing Page 1, you may need to rebuild the vector database.")
    print("\nRun:")
    print("  python delete_vector_db.py")
    print("  python build_vector_db.py")
