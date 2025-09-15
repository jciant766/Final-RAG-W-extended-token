#!/usr/bin/env python3
import json
from collections import defaultdict

def fix_duplicate_ids():
    """Fix duplicate IDs in the chunks by making them unique"""
    print("Fixing duplicate IDs in chunks...")
    
    with open('all_processed_chunks.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks)} chunks")
    
    # Track ID counts
    id_counts = defaultdict(int)
    fixed_chunks = []
    
    for chunk in chunks:
        original_id = chunk['id']
        id_counts[original_id] += 1
        
        if id_counts[original_id] > 1:
            # Create unique ID by appending counter
            new_id = f"{original_id}_{id_counts[original_id]}"
            chunk['id'] = new_id
            print(f"Fixed duplicate ID: {original_id} -> {new_id}")
        
        fixed_chunks.append(chunk)
    
    # Save fixed chunks
    with open('all_processed_chunks_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(fixed_chunks, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Fixed {len(fixed_chunks)} chunks")
    print("✓ Saved to all_processed_chunks_fixed.json")
    
    return fixed_chunks

if __name__ == "__main__":
    fix_duplicate_ids()

