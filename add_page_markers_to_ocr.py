"""
Add page markers to OCR-processed text files that are missing them.

This script analyzes OCR output and inserts page markers based on:
- Page header/footer patterns
- Article density (articles per section)
- Approximate page breaks based on character count
"""

import re
import os
from pathlib import Path

def estimate_pages_and_add_markers(input_file: Path, output_file: Path):
    """
    Add page markers to text file based on heuristics.
    
    Strategy:
    1. Detect existing page headers/footers (e.g., "CHAPTER 615", page numbers)
    2. Use article density to estimate pages
    3. Fallback to character-based estimation (~3000 chars per page)
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has page markers
    if re.search(r'---\s*PAGE\s*\d+\s*---', content, re.IGNORECASE):
        print(f"  [OK] {input_file.name} already has page markers")
        return False
    
    # Strategy 1: Detect page headers/footers
    # Common patterns: "CHAPTER 615", "Cap. 123.", page numbers at line start
    page_header_pattern = re.compile(
        r'^(?:CHAPTER|Cap\.|## CHAPTER)\s+\d+|^\d+\s*$',
        re.MULTILINE
    )
    
    # Strategy 2: Split by markdown headers (## TITLE) - rough page estimation
    section_headers = list(re.finditer(r'^## [A-Z]', content, re.MULTILINE))
    
    # Strategy 3: Character-based estimation (2500-3500 chars per page typical)
    CHARS_PER_PAGE = 3000
    estimated_pages = max(1, len(content) // CHARS_PER_PAGE)
    
    # Use heuristic: if many section headers, use those; otherwise use char count
    if len(section_headers) > 3:
        # Insert page markers at major sections
        result = []
        current_page = 1
        last_pos = 0
        
        for idx, match in enumerate(section_headers):
            section_text = content[last_pos:match.start()]
            result.append(f"--- PAGE {current_page} ---\n")
            result.append(section_text)
            current_page += 1
            last_pos = match.start()
        
        # Add remaining content
        result.append(f"--- PAGE {current_page} ---\n")
        result.append(content[last_pos:])
        
        modified_content = ''.join(result)
        page_count = current_page
    else:
        # Fallback: Split by character count
        result = []
        current_page = 1
        current_pos = 0
        
        while current_pos < len(content):
            # Find a good break point (end of paragraph or sentence)
            end_pos = min(current_pos + CHARS_PER_PAGE, len(content))
            
            # Try to break at paragraph
            next_paragraph = content.find('\n\n', end_pos - 200, end_pos + 200)
            if next_paragraph != -1 and next_paragraph < len(content):
                end_pos = next_paragraph + 2
            
            chunk = content[current_pos:end_pos]
            result.append(f"--- PAGE {current_page} ---\n")
            result.append(chunk)
            
            current_page += 1
            current_pos = end_pos
        
        modified_content = ''.join(result)
        page_count = current_page - 1
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    return page_count


def main():
    input_dir = Path('ocr/output')
    output_dir = Path('ocr/output_with_pages')
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("Adding Page Markers to OCR Output Files")
    print("=" * 80)
    
    files_processed = 0
    total_pages = 0
    
    for txt_file in sorted(input_dir.glob('*.txt')):
        print(f"\nProcessing: {txt_file.name}")
        output_file = output_dir / txt_file.name
        
        try:
            page_count = estimate_pages_and_add_markers(txt_file, output_file)
            
            if page_count:
                files_processed += 1
                total_pages += page_count
                print(f"  [OK] Added {page_count} page markers -> {output_file.name}")
            
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Files processed: {files_processed}")
    print(f"  Total pages added: {total_pages}")
    print(f"  Output directory: {output_dir}")
    print("=" * 80)
    
    print("\n[!] NEXT STEPS:")
    print("1. Review output files in 'ocr/output_with_pages/'")
    print("2. If satisfied, replace original files:")
    print("   Copy-Item ocr/output_with_pages/*.txt ocr/output/")
    print("3. Rebuild vector database:")
    print("   python rebuild_database.py")


if __name__ == '__main__':
    main()

