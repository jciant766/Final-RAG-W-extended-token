"""
Bulk Re-extraction Script for Incomplete/Empty Extractions
Uses Gemini API to re-extract laws that are missing content.

Usage:
    python bulk_reextract.py                    # Extract all pending laws
    python bulk_reextract.py --list             # Just list what needs extraction
    python bulk_reextract.py --start-from 50    # Resume from index 50
    python bulk_reextract.py --only-critical    # Only extract critical (>100 pages missing)
    python bulk_reextract.py --single "Cap. 9"  # Extract single law
"""

import json
import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

# Import the extraction infrastructure
from graph_rag_extraction import (
    process_law,
    save_extraction,
    LAWS_TO_EXTRACT
)

# Build lookup maps
CAP_TO_PDF = {law['cap']: law['pdf_path'] for law in LAWS_TO_EXTRACT}
CAP_TO_NAME = {law['cap']: law['name'] for law in LAWS_TO_EXTRACT}

def get_laws_needing_extraction():
    """Analyze all extractions and return list of laws needing re-extraction."""

    extractions_dir = Path('extractions')

    needs_extraction = []

    for ext_file in sorted(extractions_dir.glob('extraction_*.json')):
        try:
            with open(ext_file, encoding='utf-8') as f:
                data = json.load(f)

            law_code = data.get('law_code', '')
            articles = data.get('articles', [])
            schedules = data.get('schedules', [])

            pdf_path = CAP_TO_PDF.get(law_code)
            if not pdf_path or not os.path.exists(pdf_path):
                continue

            doc = fitz.open(pdf_path)
            pdf_pages = doc.page_count
            doc.close()

            # Case 1: Empty extraction
            if len(articles) == 0 and len(schedules) == 0:
                if pdf_pages > 2:  # Skip tiny PDFs
                    needs_extraction.append({
                        'code': law_code,
                        'name': CAP_TO_NAME.get(law_code, ''),
                        'pdf_path': pdf_path,
                        'pdf_pages': pdf_pages,
                        'current_articles': 0,
                        'pages_missing': pdf_pages,
                        'reason': 'empty'
                    })
                continue

            # Case 2: Incomplete extraction
            all_items = articles + schedules
            max_page = max([item.get('page_end') or item.get('page_start') or 0 for item in all_items])

            coverage = max_page / pdf_pages * 100 if pdf_pages > 0 else 0
            pages_missing = pdf_pages - max_page

            if coverage < 80 and pages_missing > 10:
                needs_extraction.append({
                    'code': law_code,
                    'name': CAP_TO_NAME.get(law_code, ''),
                    'pdf_path': pdf_path,
                    'pdf_pages': pdf_pages,
                    'current_articles': len(articles),
                    'last_page': max_page,
                    'pages_missing': pages_missing,
                    'coverage': coverage,
                    'reason': 'incomplete'
                })

        except Exception as e:
            print(f"Error checking {ext_file}: {e}")

    # Sort by pages_missing descending (most critical first)
    needs_extraction.sort(key=lambda x: -x['pages_missing'])

    return needs_extraction


def print_extraction_list(laws):
    """Print formatted list of laws needing extraction."""

    critical = [l for l in laws if l['pages_missing'] > 100]
    medium = [l for l in laws if 50 < l['pages_missing'] <= 100]
    low = [l for l in laws if 10 < l['pages_missing'] <= 50]
    empty = [l for l in laws if l['reason'] == 'empty']

    print("\n" + "=" * 90)
    print("LAWS NEEDING RE-EXTRACTION")
    print("=" * 90)

    print(f"\n{'='*40}")
    print(f"CRITICAL ({len(critical)} laws, >100 pages missing)")
    print(f"{'='*40}")
    for i, law in enumerate(critical):
        print(f"  {i+1:3}. {law['code']:<15} {law['name'][:45]:<45} {law['pages_missing']:>4} pages")

    print(f"\n{'='*40}")
    print(f"MEDIUM ({len(medium)} laws, 50-100 pages missing)")
    print(f"{'='*40}")
    for i, law in enumerate(medium):
        print(f"  {i+1:3}. {law['code']:<15} {law['name'][:45]:<45} {law['pages_missing']:>4} pages")

    print(f"\n{'='*40}")
    print(f"LOW PRIORITY ({len(low)} laws, 10-50 pages missing)")
    print(f"{'='*40}")
    print(f"  (Mostly tax treaties and housing documents)")

    print(f"\n{'='*40}")
    print(f"EMPTY EXTRACTIONS ({len(empty)} laws)")
    print(f"{'='*40}")
    for i, law in enumerate(empty[:20]):
        print(f"  {i+1:3}. {law['code']:<15} {law['name'][:45]:<45} {law['pdf_pages']:>4} pages")
    if len(empty) > 20:
        print(f"  ... and {len(empty) - 20} more")

    print(f"\n{'='*90}")
    print(f"TOTAL: {len(laws)} laws need re-extraction")
    total_pages = sum(l['pages_missing'] for l in laws)
    print(f"TOTAL PAGES TO PROCESS: {total_pages:,}")
    print(f"ESTIMATED TIME: {total_pages * 3 / 60:.1f} - {total_pages * 5 / 60:.1f} minutes")
    print("=" * 90)


def save_progress(completed, failed, progress_file="extraction_progress.json"):
    """Save extraction progress for resume capability."""
    with open(progress_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'completed': completed,
            'failed': failed
        }, f, indent=2)


def load_progress(progress_file="extraction_progress.json"):
    """Load previous extraction progress."""
    if Path(progress_file).exists():
        with open(progress_file) as f:
            return json.load(f)
    return {'completed': [], 'failed': []}


def extract_single_law(law_info, index, total):
    """Extract a single law and return success status."""

    code = law_info['code']
    name = law_info['name']
    pdf_path = law_info['pdf_path']

    print(f"\n{'='*70}")
    print(f"[{index}/{total}] Extracting: {code}")
    print(f"Name: {name}")
    print(f"PDF: {pdf_path} ({law_info['pdf_pages']} pages)")
    print(f"Reason: {law_info['reason']}")
    print(f"{'='*70}")

    try:
        start_time = time.time()

        extraction = process_law(
            pdf_path=pdf_path,
            cap=code,
            law_name=name,
            page_range=None
        )

        if extraction:
            output_file = save_extraction(extraction, output_dir="extractions")
            elapsed = time.time() - start_time

            # Verify extraction
            with open(output_file) as f:
                data = json.load(f)

            articles = len(data.get('articles', []))
            schedules = len(data.get('schedules', []))

            print(f"\n[SUCCESS] {code}: {articles} articles, {schedules} schedules")
            print(f"Time: {elapsed:.1f}s | Output: {output_file}")

            return True, {
                'code': code,
                'articles': articles,
                'schedules': schedules,
                'time': elapsed
            }
        else:
            print(f"\n[FAILED] {code}: No extraction returned")
            return False, {'code': code, 'error': 'No extraction returned'}

    except Exception as e:
        print(f"\n[ERROR] {code}: {str(e)}")
        return False, {'code': code, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Bulk re-extract incomplete/empty laws')
    parser.add_argument('--list', action='store_true', help='Just list laws needing extraction')
    parser.add_argument('--start-from', type=int, default=0, help='Start from index N')
    parser.add_argument('--limit', type=int, default=None, help='Limit to N extractions')
    parser.add_argument('--only-critical', action='store_true', help='Only extract critical (>100 pages)')
    parser.add_argument('--only-empty', action='store_true', help='Only extract empty extractions')
    parser.add_argument('--single', type=str, help='Extract single law by code (e.g., "Cap. 9")')
    parser.add_argument('--resume', action='store_true', help='Resume from previous progress')

    args = parser.parse_args()

    print("=" * 90)
    print("BULK RE-EXTRACTION SCRIPT")
    print("=" * 90)
    print("Analyzing extractions...")

    # Get list of laws needing extraction
    all_laws = get_laws_needing_extraction()

    if args.list:
        print_extraction_list(all_laws)
        return 0

    # Filter based on arguments
    if args.single:
        laws_to_extract = [l for l in all_laws if l['code'] == args.single]
        if not laws_to_extract:
            print(f"ERROR: Law '{args.single}' not found in extraction list")
            return 1
    elif args.only_critical:
        laws_to_extract = [l for l in all_laws if l['pages_missing'] > 100]
    elif args.only_empty:
        laws_to_extract = [l for l in all_laws if l['reason'] == 'empty']
    else:
        laws_to_extract = all_laws

    # Apply start-from and limit
    if args.start_from > 0:
        laws_to_extract = laws_to_extract[args.start_from:]
    if args.limit:
        laws_to_extract = laws_to_extract[:args.limit]

    # Load previous progress if resuming
    if args.resume:
        progress = load_progress()
        completed_codes = set(progress['completed'])
        laws_to_extract = [l for l in laws_to_extract if l['code'] not in completed_codes]
        print(f"Resuming... {len(completed_codes)} already completed, {len(laws_to_extract)} remaining")

    if not laws_to_extract:
        print("No laws to extract!")
        return 0

    print(f"\nWill extract {len(laws_to_extract)} laws")
    total_pages = sum(l['pages_missing'] for l in laws_to_extract)
    print(f"Total pages: {total_pages:,}")
    print(f"Estimated time: {total_pages * 3 / 60:.1f} - {total_pages * 5 / 60:.1f} minutes")
    print()

    # Confirm before proceeding
    if not args.single:
        response = input("Proceed with extraction? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0

    # Track progress
    completed = []
    failed = []
    start_time = time.time()

    try:
        for i, law in enumerate(laws_to_extract, 1):
            success, result = extract_single_law(law, i, len(laws_to_extract))

            if success:
                completed.append(law['code'])
            else:
                failed.append(result)

            # Save progress after each extraction
            save_progress(completed, failed)

            # Rate limiting - pause between extractions
            if i < len(laws_to_extract):
                time.sleep(1)  # 1 second pause

    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        save_progress(completed, failed)

    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 90)
    print("EXTRACTION COMPLETE")
    print("=" * 90)
    print(f"Completed: {len(completed)}/{len(laws_to_extract)}")
    print(f"Failed: {len(failed)}")
    print(f"Total time: {elapsed/60:.1f} minutes")

    if failed:
        print("\nFailed extractions:")
        for f in failed:
            print(f"  - {f['code']}: {f.get('error', 'Unknown error')}")

    print("\nProgress saved to extraction_progress.json")
    print("\nNext steps:")
    print("1. Review any failed extractions")
    print("2. Run database re-ingestion for completed extractions")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
