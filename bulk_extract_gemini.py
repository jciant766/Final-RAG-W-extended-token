"""
Bulk Extraction Script using Standard Gemini API
Extracts articles from incomplete/empty law PDFs.

Usage:
    python bulk_extract_gemini.py --list             # List what needs extraction
    python bulk_extract_gemini.py --start-from 0     # Start extraction
    python bulk_extract_gemini.py --single "Cap. 9"  # Extract single law
    python bulk_extract_gemini.py --limit 10         # Limit to N laws
"""

import json
import sys
import os
import time
import argparse
import base64
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import fitz  # PyMuPDF

import google.generativeai as genai

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Get API key
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY not set in .env file")
    sys.exit(1)

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Model to use
MODEL_NAME = "gemini-2.5-flash"

# Load laws list
LAWS_FILE = "laws_to_extract.json"
with open(LAWS_FILE) as f:
    LAWS_TO_EXTRACT = json.load(f)

CAP_TO_PDF = {law['cap']: law['pdf_path'] for law in LAWS_TO_EXTRACT}
CAP_TO_NAME = {law['cap']: law['name'] for law in LAWS_TO_EXTRACT}

# Rate limiting
REQUESTS_PER_MINUTE = 10  # Conservative limit
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE

# =============================================================================
# EXTRACTION PROMPT
# =============================================================================

def build_extraction_prompt(law_name: str, cap: str, is_subsidiary: bool) -> str:
    """Build the extraction prompt for a page."""

    item_type = "regulation" if is_subsidiary else "article"
    item_type_plural = "regulations" if is_subsidiary else "articles"

    return f"""You are extracting legal content from a Maltese law PDF page.

LAW: {law_name} ({cap})
CONTENT TYPE: {item_type_plural.upper()}

Extract all {item_type_plural} from this page. Return a JSON object with this structure:

{{
    "page_content_type": "articles" | "schedule" | "skip",
    "{item_type_plural}": [
        {{
            "number": "1",
            "title": "Title of the {item_type}",
            "text": "Full text including all sub-{item_type}s",
            "sub_items": ["1(1)", "1(2)", "1(2)(a)"],
            "cross_references": {{
                "internal": ["5", "10(2)"],
                "external": [{{"law": "Cap. 16", "article": "1045"}}]
            }}
        }}
    ],
    "schedules": [
        {{
            "name": "First Schedule",
            "title": "Schedule Title",
            "text": "Schedule content"
        }}
    ],
    "last_{item_type}_on_page": "5",
    "last_{item_type}_ended": true,
    "continues_from_previous": false
}}

RULES:
1. Extract COMPLETE text for each {item_type} including all sub-items
2. Keep {item_type}s as single chunks - don't split sub-{item_type}s
3. If page has no {item_type_plural}, use page_content_type: "skip" or "schedule"
4. Track cross-references to other articles/laws
5. Return ONLY valid JSON

Return ONLY the JSON object, no other text."""


# =============================================================================
# PAGE PROCESSING
# =============================================================================

def page_to_base64(page: fitz.Page, dpi: int = 150) -> str:
    """Convert PDF page to base64 PNG."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode('utf-8')


def extract_page(model, page: fitz.Page, law_name: str, cap: str,
                 is_subsidiary: bool, page_num: int, context: Dict) -> Optional[Dict]:
    """Extract content from a single page."""

    prompt = build_extraction_prompt(law_name, cap, is_subsidiary)

    # Add context about previous page
    if context.get('last_item'):
        prompt += f"\n\nPREVIOUS PAGE ended with {context['item_type']} {context['last_item']}"
        if not context.get('last_ended', True):
            prompt += " (CONTINUES on this page)"

    # Convert page to image
    img_base64 = page_to_base64(page)

    try:
        response = model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": img_base64}
        ])

        # Parse response
        text = response.text.strip()

        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"    [Page {page_num}] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    [Page {page_num}] Error: {e}")
        return None


def is_subsidiary_legislation(cap: str) -> bool:
    """Check if law code is subsidiary legislation."""
    return cap.startswith('S.L.')


def generate_item_id(cap: str, number: str) -> str:
    """Generate unique ID for an article/regulation."""
    prefix = "reg" if is_subsidiary_legislation(cap) else "art"
    normalized_cap = cap.replace(' ', '').replace('.', '.')
    return f"{prefix}:{normalized_cap}/{number}"


# =============================================================================
# LAW PROCESSING
# =============================================================================

def process_law(pdf_path: str, cap: str, law_name: str,
                existing_metadata: Optional[Dict] = None) -> Optional[Dict]:
    """Process a complete law PDF."""

    print(f"\n{'='*60}")
    print(f"Processing: {law_name} ({cap})")
    print(f"PDF: {pdf_path}")
    print(f"{'='*60}")

    is_subsidiary = is_subsidiary_legislation(cap)
    item_type = "regulation" if is_subsidiary else "article"
    content_key = "regulations" if is_subsidiary else "articles"

    # Initialize model
    model = genai.GenerativeModel(MODEL_NAME)

    # Open PDF
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return None

    total_pages = doc.page_count
    print(f"Total pages: {total_pages}")

    # Collect extracted content
    all_items = []
    all_schedules = []
    context = {'item_type': item_type}

    # Process each page
    for page_num in range(total_pages):
        page = doc[page_num]

        print(f"  Page {page_num + 1}/{total_pages}...", end=" ", flush=True)

        result = extract_page(model, page, law_name, cap, is_subsidiary, page_num + 1, context)

        if result:
            # Collect items
            items = result.get(content_key, [])
            for item in items:
                item['page_start'] = page_num + 1
                item['page_end'] = page_num + 1
                item['id'] = generate_item_id(cap, item.get('number', ''))
                all_items.append(item)

            # Collect schedules
            schedules = result.get('schedules', [])
            for sched in schedules:
                sched['page_start'] = page_num + 1
                sched['page_end'] = page_num + 1
                all_schedules.append(sched)

            # Update context
            if items:
                context['last_item'] = items[-1].get('number')
                context['last_ended'] = result.get(f'last_{item_type}_ended', True)

            print(f"OK ({len(items)} {content_key})")
        else:
            print("SKIP")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    doc.close()

    # Build extraction result
    extraction = {
        'law_code': cap,
        'law_name': law_name,
        'law_type': 'subsidiary' if is_subsidiary else 'chapter',
        'metadata': existing_metadata or {},
        'articles': all_items if not is_subsidiary else [],
        'regulations': all_items if is_subsidiary else [],
        'schedules': all_schedules,
        'miscellaneous': []
    }

    # Use 'articles' as the standard key
    if is_subsidiary:
        extraction['articles'] = extraction.pop('regulations')

    return extraction


# =============================================================================
# MAIN LOGIC
# =============================================================================

def get_laws_needing_extraction() -> List[Dict]:
    """Get list of laws needing extraction."""

    extractions_dir = Path('extractions')
    needs_extraction = []

    for ext_file in sorted(extractions_dir.glob('extraction_*.json')):
        try:
            with open(ext_file, encoding='utf-8') as f:
                data = json.load(f)

            law_code = data.get('law_code', '')
            articles = data.get('articles', [])
            schedules = data.get('schedules', [])
            metadata = data.get('metadata', {})

            pdf_path = CAP_TO_PDF.get(law_code)
            if not pdf_path or not os.path.exists(pdf_path):
                continue

            doc = fitz.open(pdf_path)
            pdf_pages = doc.page_count
            doc.close()

            # Case 1: Empty extraction
            if len(articles) == 0 and len(schedules) == 0:
                if pdf_pages > 2:
                    needs_extraction.append({
                        'code': law_code,
                        'name': CAP_TO_NAME.get(law_code, ''),
                        'pdf_path': pdf_path,
                        'pdf_pages': pdf_pages,
                        'current_articles': 0,
                        'pages_missing': pdf_pages,
                        'reason': 'empty',
                        'metadata': metadata
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
                    'reason': 'incomplete',
                    'metadata': metadata
                })

        except Exception as e:
            pass

    # Sort by pages_missing descending
    needs_extraction.sort(key=lambda x: -x['pages_missing'])

    return needs_extraction


def save_extraction(extraction: Dict, output_dir: str = "extractions") -> str:
    """Save extraction to JSON file."""

    cap = extraction['law_code']
    filename = f"extraction_{cap.replace(' ', '').replace('.', '.')}.json"
    filepath = Path(output_dir) / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(extraction, f, indent=2, ensure_ascii=False)

    return str(filepath)


def save_progress(completed: List, failed: List, progress_file: str = "extraction_progress.json"):
    """Save progress for resume capability."""
    with open(progress_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'completed': completed,
            'failed': failed
        }, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Bulk extract laws using Gemini API')
    parser.add_argument('--list', action='store_true', help='List laws needing extraction')
    parser.add_argument('--start-from', type=int, default=0, help='Start from index N')
    parser.add_argument('--limit', type=int, help='Limit to N extractions')
    parser.add_argument('--single', type=str, help='Extract single law by code')
    parser.add_argument('--only-critical', action='store_true', help='Only >100 pages missing')

    args = parser.parse_args()

    print("=" * 60)
    print("BULK EXTRACTION - GEMINI API")
    print(f"Model: {MODEL_NAME}")
    print("=" * 60)

    # Get laws needing extraction
    all_laws = get_laws_needing_extraction()

    if args.list:
        print(f"\nTotal laws needing extraction: {len(all_laws)}")
        print(f"Total pages: {sum(l['pages_missing'] for l in all_laws):,}")

        critical = [l for l in all_laws if l['pages_missing'] > 100]
        print(f"\nCritical (>100 pages): {len(critical)}")
        for law in critical:
            print(f"  - {law['code']}: {law['name'][:40]} ({law['pages_missing']} pages)")

        return 0

    # Filter laws
    if args.single:
        laws_to_extract = [l for l in all_laws if l['code'] == args.single]
        if not laws_to_extract:
            print(f"ERROR: {args.single} not found")
            return 1
    elif args.only_critical:
        laws_to_extract = [l for l in all_laws if l['pages_missing'] > 100]
    else:
        laws_to_extract = all_laws

    # Apply start/limit
    laws_to_extract = laws_to_extract[args.start_from:]
    if args.limit:
        laws_to_extract = laws_to_extract[:args.limit]

    if not laws_to_extract:
        print("No laws to extract!")
        return 0

    total_pages = sum(l['pages_missing'] for l in laws_to_extract)
    print(f"\nWill extract {len(laws_to_extract)} laws ({total_pages:,} pages)")
    print(f"Estimated time: {total_pages * REQUEST_DELAY / 60:.1f} minutes")
    print(f"Estimated cost: ${total_pages * 0.00086:.2f} (Batch pricing)")

    if not args.single:
        response = input("\nProceed? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0

    # Process laws
    completed = []
    failed = []

    try:
        for i, law in enumerate(laws_to_extract, 1):
            print(f"\n[{i}/{len(laws_to_extract)}] {law['code']}")

            try:
                extraction = process_law(
                    pdf_path=law['pdf_path'],
                    cap=law['code'],
                    law_name=law['name'],
                    existing_metadata=law.get('metadata')
                )

                if extraction:
                    output_file = save_extraction(extraction)
                    articles = len(extraction.get('articles', []))
                    print(f"  SAVED: {articles} articles -> {output_file}")
                    completed.append(law['code'])
                else:
                    failed.append({'code': law['code'], 'error': 'No extraction returned'})

            except Exception as e:
                print(f"  ERROR: {e}")
                failed.append({'code': law['code'], 'error': str(e)})

            save_progress(completed, failed)

    except KeyboardInterrupt:
        print("\n\nInterrupted!")
        save_progress(completed, failed)

    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Completed: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed:")
        for f in failed[:10]:
            print(f"  - {f['code']}: {f['error'][:50]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
