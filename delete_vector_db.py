"""
Simple script to delete the vector database
Use this when you want to rebuild from scratch
"""

import os
import shutil
import time

def delete_vector_db():
    """Delete the ChromaDB vector database"""
    db_path = "chroma_db"
    
    if not os.path.exists(db_path):
        print("ℹ️  No vector database found to delete")
        print(f"   Looking for: {os.path.abspath(db_path)}")
        return False
    
    print(f"🗑️  Deleting vector database: {db_path}")
    
    # Try multiple times in case of temporary locks
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            shutil.rmtree(db_path)
            print("✅ Vector database deleted successfully!")
            print("\nℹ️  The database will be automatically rebuilt when you run:")
            print("   streamlit run main.py")
            return True
        except PermissionError as e:
            if attempt < max_attempts - 1:
                print(f"⚠️  Attempt {attempt + 1} failed: Database is locked")
                print("   Waiting 2 seconds and retrying...")
                time.sleep(2)
            else:
                print("\n❌ ERROR: Cannot delete database - it's being used by another process")
                print("\n🔧 SOLUTION:")
                print("   1. Close Streamlit app (Ctrl+C in terminal or close browser)")
                print("   2. Close any Python processes using the database")
                print("   3. Run this script again")
                print(f"\n   Error details: {e}")
                return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("DELETE VECTOR DATABASE")
    print("=" * 60)
    print("\n⚠️  This will delete the ChromaDB vector database.")
    print("   The database will be rebuilt on next app startup.\n")
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        delete_vector_db()
    else:
        print("❌ Operation cancelled")
