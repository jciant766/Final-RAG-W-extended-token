"""
Generate LAWS_TO_EXTRACT list for all Malta law PDFs
This script scans the PDF directory and creates the configuration list.
"""

import os
import re
import json
from pathlib import Path

def parse_law_filename(filename: str) -> tuple:
    """
    Parse law filename to extract code and name.

    Examples:
        "Criminal Code (Cap. 9).pdf" -> ("Cap. 9", "Criminal Code")
        "Companies Act (Forms) Regulations (S.L. 386.01).pdf" -> ("S.L. 386.01", "Companies Act (Forms) Regulations")
        "Building Act (S.L. 595.33(R)).pdf" -> ("S.L. 595.33", "Building Act [R]")
        "Justice Rules (S.L.Const.04).pdf" -> ("S.L. Const.04", "Justice Rules")

    Returns:
        (code, name) tuple
    """
    name = filename.replace('.pdf', '')

    # Try to match Cap. pattern (with optional (R) for revised)
    # Also matches "Cap 123" without the period
    cap_match = re.search(r'\(Cap\.?\s*(\d+)(?:\(R\))?\)', name, re.IGNORECASE)
    if cap_match:
        code = f"Cap. {cap_match.group(1)}"
        # Extract full match to remove from name
        full_match = cap_match.group(0)
        clean_name = name.replace(full_match, "").strip()
        # Add [R] indicator if it was revised
        if '(R)' in full_match.upper():
            clean_name = f"{clean_name} [R]"
        return (code, clean_name)

    # Try to match S.L. pattern (with optional (R), and allowing non-numeric like Const.04)
    # Pattern 1: S.L. 123.45 or S.L. 123.45(R)
    sl_match = re.search(r'\(S\.L\.\s*([\d.]+)(?:\(R\))?\)', name, re.IGNORECASE)
    if sl_match:
        code = f"S.L. {sl_match.group(1)}"
        full_match = sl_match.group(0)
        clean_name = name.replace(full_match, "").strip()
        if '(R)' in full_match.upper():
            clean_name = f"{clean_name} [R]"
        return (code, clean_name)

    # Pattern 2: S.L.Const.04 or S.L. const.06 (no parentheses or with)
    sl_const_match = re.search(r'\(S\.L\.\s*([A-Za-z]+\.[\d]+)\)', name, re.IGNORECASE)
    if sl_const_match:
        code = f"S.L. {sl_const_match.group(1).title()}"  # Title case for consistency
        full_match = sl_const_match.group(0)
        clean_name = name.replace(full_match, "").strip()
        return (code, clean_name)

    # Fallback: Generate code from filename (for edge cases with no standard code)
    # Use first 50 chars or up to first special char as code
    clean_name = name
    # Generate a simple code from the filename
    code_base = re.sub(r'[^a-zA-Z0-9]', '', name[:30])  # Clean alphanumeric
    code = f"MISC.{code_base[:20]}" if code_base else "MISC.Unknown"

    return (code, clean_name)


def generate_extraction_list(pdf_dir: str = "All Malta law PDFs") -> list:
    """
    Generate LAWS_TO_EXTRACT list from all PDFs in directory.

    Returns:
        List of law dictionaries ready for LAWS_TO_EXTRACT
    """
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Directory not found: {pdf_dir}")

    # Get all PDF files
    pdf_files = sorted(pdf_path.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files in '{pdf_dir}'")

    laws = []

    for pdf_file in pdf_files:
        code, name = parse_law_filename(pdf_file.name)

        law_entry = {
            "pdf_path": f"{pdf_dir}/{pdf_file.name}",
            "cap": code,
            "name": name,
            "page_range": None  # Extract all pages
        }
        laws.append(law_entry)

    print(f"Successfully parsed: {len(laws)} laws (all {len(pdf_files)} PDFs)")

    return laws


def write_extraction_config(laws: list, output_file: str = "laws_to_extract.json"):
    """Write the laws list to a JSON file for easy inspection."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(laws, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Wrote extraction config to: {output_file}")
    print(f"  Total laws: {len(laws)}")


def print_python_snippet(laws: list, max_preview: int = 5):
    """Print a Python code snippet to paste into graph_rag_extraction.py"""
    print("\n" + "="*80)
    print("COPY THIS INTO graph_rag_extraction.py")
    print("="*80)
    print("\n# List of laws to extract (each will create a separate JSON file)")
    print("LAWS_TO_EXTRACT = [")

    # Show first few as preview
    for law in laws[:max_preview]:
        print(f"    {{")
        print(f"        \"pdf_path\": \"{law['pdf_path']}\",")
        print(f"        \"cap\": \"{law['cap']}\",")
        print(f"        \"name\": \"{law['name']}\",")
        print(f"        \"page_range\": None  # All pages")
        print(f"    }},")

    if len(laws) > max_preview:
        print(f"    # ... {len(laws) - max_preview} more laws ...")
        print(f"    # See laws_to_extract.json for full list")

    print("]")
    print("\n" + "="*80)


def main():
    print("\n" + "="*80)
    print("MALTA LAWS - EXTRACTION LIST GENERATOR")
    print("="*80)

    # Generate the list
    laws = generate_extraction_list()

    # Write to JSON file
    write_extraction_config(laws)

    # Print Python snippet
    print_python_snippet(laws)

    # Statistics
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)

    cap_count = sum(1 for law in laws if law['cap'].startswith('Cap.'))
    sl_count = sum(1 for law in laws if law['cap'].startswith('S.L.'))
    misc_count = sum(1 for law in laws if law['cap'].startswith('MISC.'))

    print(f"  Parent Laws (Cap.): {cap_count}")
    print(f"  Subsidiary Laws (S.L.): {sl_count}")
    if misc_count > 0:
        print(f"  Miscellaneous/Other (MISC.): {misc_count}")
    print(f"  Total: {len(laws)}")

    # Estimation
    avg_pages_per_law = 30  # Conservative estimate
    total_pages_estimate = len(laws) * avg_pages_per_law
    time_per_page_seconds = 5  # Conservative estimate
    total_time_hours = (total_pages_estimate * time_per_page_seconds) / 3600

    print(f"\n  Estimated total pages: ~{total_pages_estimate:,}")
    print(f"  Estimated processing time: ~{total_time_hours:.1f} hours")
    print(f"    (assumes ~{avg_pages_per_law} pages/law, ~{time_per_page_seconds}s/page)")

    print("\n[OK] Done! Use the JSON file or copy the Python snippet above.")
    print()


if __name__ == "__main__":
    main()
