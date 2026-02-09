"""
Re-extract Criminal Code (Cap. 9) completely.
This script extracts the full 422-page Criminal Code PDF.
"""

import json
import sys
from pathlib import Path

# Import the extraction infrastructure
from graph_rag_extraction import (
    process_law,
    save_extraction,
    LAWS_TO_EXTRACT
)

def main():
    """Re-extract Cap. 9 only."""

    # Find Cap. 9 in the laws list
    cap9_law = None
    for law in LAWS_TO_EXTRACT:
        if law['cap'] == 'Cap. 9':
            cap9_law = law
            break

    if not cap9_law:
        print("ERROR: Cap. 9 not found in laws_to_extract.json")
        return 1

    print("=" * 80)
    print("RE-EXTRACTING CRIMINAL CODE (CAP. 9)")
    print("=" * 80)
    print(f"PDF: {cap9_law['pdf_path']}")
    print(f"Law: {cap9_law['name']}")
    print()
    print("This will take approximately 45-90 minutes for 422 pages.")
    print("Progress will be shown as pages are processed.")
    print("=" * 80)
    print()

    # Check if PDF exists
    pdf_path = Path(cap9_law['pdf_path'])
    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return 1

    # Run extraction
    try:
        extraction = process_law(
            pdf_path=str(pdf_path),
            cap=cap9_law['cap'],
            law_name=cap9_law['name'],
            page_range=None  # Extract all pages
        )

        if extraction:
            # Save the extraction
            output_file = save_extraction(extraction, output_dir="extractions")
            print()
            print("=" * 80)
            print("EXTRACTION COMPLETE!")
            print("=" * 80)

            # Load and show stats
            if Path(output_file).exists():
                with open(output_file) as f:
                    data = json.load(f)

                articles = data.get('articles', [])
                schedules = data.get('schedules', [])

                print(f"Output file: {output_file}")
                print(f"Articles extracted: {len(articles)}")
                print(f"Schedules extracted: {len(schedules)}")

                if articles:
                    article_nums = [a.get('number') for a in articles]
                    print(f"Article range: {article_nums[0]} to {article_nums[-1]}")

                    # Get page coverage
                    max_page = max([a.get('page_end', 0) or 0 for a in articles])
                    print(f"Pages extracted: 1 to {max_page}")

                print()
                print("Next steps:")
                print("1. Remove old Cap. 9 data from database")
                print("2. Re-ingest the new extraction")

            return 0
        else:
            print("ERROR: Extraction failed")
            return 1

    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user.")
        print("Partial extraction may have been saved.")
        return 1
    except Exception as e:
        print(f"\nERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
