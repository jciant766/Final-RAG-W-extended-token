"""
Rebuild Vector Database with Page Numbers
Safely deletes and rebuilds the vector database to include page markers
"""

import os
import shutil
import sys
import time

print("=" * 80)
print("REBUILD VECTOR DATABASE WITH PAGE NUMBERS")
print("=" * 80)

# Check if database exists
if not os.path.exists('chroma_db'):
    print("\nNo existing database found. Will build fresh database.")
else:
    print("\nExisting database found.")
    print("\nIMPORTANT: Close any running applications that might be using the database:")
    print("  - Streamlit app")
    print("  - Jupyter notebooks")
    print("  - Python shells")

    response = input("\nHave you closed all applications? (yes/no): ").lower()
    if response != 'yes':
        print("\nPlease close all applications and run this script again.")
        sys.exit(0)

    print("\nAttempting to delete old database...")

    try:
        # Try to delete
        shutil.rmtree('chroma_db')
        print("[SUCCESS] Old database deleted")
    except PermissionError as e:
        print(f"\n[ERROR] Cannot delete database - file is in use:")
        print(f"  {e}")
        print("\nPlease:")
        print("  1. Close all Python processes (Streamlit, notebooks, etc.)")
        print("  2. Wait 5 seconds")
        print("  3. Run this script again")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)

# Build new database
print("\n" + "=" * 80)
print("BUILDING NEW DATABASE WITH PAGE MARKERS")
print("=" * 80)

print("\nThis will process:")
print("  - 1 commercial code file")
print("  - 43 OCR output files")
print("  - Total: 44 documents")
print("\nEstimated time: 2-5 minutes")
print("\nStarting build...\n")

# Import and run build script
try:
    # Run build_vector_db.py
    exec(open('build_vector_db.py').read())

    print("\n" + "=" * 80)
    print("REBUILD COMPLETE!")
    print("=" * 80)
    print("\nPage numbers are now included in the vector database.")
    print("\nExpected results:")
    print("  - 34 documents with accurate page numbers (79%)")
    print("  - 9 small documents showing 'Page 1' (21%)")
    print("\nTo test:")
    print("  streamlit run main.py")
    print("\nThen search for something and check the 'Sources Referenced' section.")
    print("You should see citations like:")
    print("  - Civil Code (Cap. 16) - Art. 1123 (Page 187)")
    print("  - Income Tax Act (Cap. 123) - Art. 4 (Page 12)")

except Exception as e:
    print(f"\n[ERROR] Build failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
