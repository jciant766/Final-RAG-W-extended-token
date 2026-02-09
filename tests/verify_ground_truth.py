"""
Verify Ground Truth for RAG Test Questions.

This script searches the RAW extraction JSON files (not the vector DB)
to confirm that expected keywords actually exist in expected laws.

This gives us independent verification that our test questions have valid ground truth.

Usage:
    python tests/verify_ground_truth.py
    python tests/verify_ground_truth.py --question TRAFFIC-001
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from comprehensive_rag_eval import TEST_QUESTIONS, TestQuestion


def load_all_extractions(extractions_dir: str = "extractions") -> Dict[str, Dict]:
    """
    Load all extraction JSON files into memory.

    Returns:
        Dict mapping law_code -> extraction data
    """
    extractions = {}
    extractions_path = Path(extractions_dir)

    if not extractions_path.exists():
        print(f"ERROR: Extractions directory not found: {extractions_dir}")
        return {}

    json_files = list(extractions_path.glob("*.json"))
    print(f"Loading {len(json_files)} extraction files...")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                law_code = data.get("law_code", "")
                if law_code:
                    extractions[law_code] = data
                    # Also store with normalized code (e.g., "S.L.65.11" and "S.L. 65.11")
                    normalized = law_code.replace(" ", "")
                    if normalized != law_code:
                        extractions[normalized] = data
        except Exception as e:
            print(f"  Warning: Could not load {json_file.name}: {e}")

    print(f"Loaded {len(extractions)} unique laws")
    return extractions


def get_all_text_from_law(law_data: Dict) -> str:
    """Extract all searchable text from a law extraction."""
    texts = []

    # Law summary/metadata
    metadata = law_data.get("metadata", {}) or {}
    texts.append(metadata.get("purpose", "") or "")
    texts.append(metadata.get("summary_text", "") or "")
    key_topics = metadata.get("key_topics", []) or []
    texts.append(" ".join([t for t in key_topics if t]))

    # Articles
    for article in law_data.get("articles", []) or []:
        texts.append(article.get("text", "") or "")
        texts.append(article.get("title", "") or "")

    # Regulations (for S.L.)
    for reg in law_data.get("regulations", []) or []:
        texts.append(reg.get("text", "") or "")
        texts.append(reg.get("title", "") or "")

    # Schedules
    for schedule in law_data.get("schedules", []) or []:
        texts.append(schedule.get("text", "") or "")
        texts.append(schedule.get("title", "") or "")

    # Filter out None values and join
    return " ".join([t for t in texts if t]).lower()


def find_law(law_code: str, extractions: Dict[str, Dict]) -> Dict:
    """Find a law by code, handling variations."""
    # Direct match
    if law_code in extractions:
        return extractions[law_code]

    # Try without spaces
    no_space = law_code.replace(" ", "")
    if no_space in extractions:
        return extractions[no_space]

    # Try with spaces
    with_space = law_code.replace(".", ". ")
    if with_space in extractions:
        return extractions[with_space]

    # Partial match
    for code, data in extractions.items():
        if law_code in code or code in law_code:
            return data

    return None


def verify_question(question: TestQuestion, extractions: Dict[str, Dict]) -> Dict:
    """
    Verify a single test question against raw extractions.

    Returns:
        Dict with verification results
    """
    result = {
        "id": question.id,
        "query": question.query,
        "valid": True,
        "laws_verified": [],
        "laws_missing": [],
        "keywords_found": {},
        "keywords_missing": {},
        "issues": []
    }

    for expected_law in question.expected_laws:
        law_data = find_law(expected_law, extractions)

        if law_data is None:
            result["laws_missing"].append(expected_law)
            result["issues"].append(f"Law {expected_law} not found in extractions")
            result["valid"] = False
            continue

        result["laws_verified"].append(expected_law)

        # Search for expected keywords in this law
        law_text = get_all_text_from_law(law_data)

        found_in_law = []
        missing_in_law = []

        for keyword in question.expected_keywords:
            if keyword.lower() in law_text:
                found_in_law.append(keyword)
            else:
                missing_in_law.append(keyword)

        result["keywords_found"][expected_law] = found_in_law
        result["keywords_missing"][expected_law] = missing_in_law

        # If no keywords found in this law, it's a problem
        if len(found_in_law) == 0 and len(question.expected_keywords) > 0:
            result["issues"].append(f"No expected keywords found in {expected_law}")

    # Check if at least SOME keywords were found somewhere
    all_found = set()
    for kws in result["keywords_found"].values():
        all_found.update(kws)

    all_missing = set(question.expected_keywords) - all_found
    if all_missing and len(all_missing) == len(question.expected_keywords):
        result["valid"] = False
        result["issues"].append(f"No keywords found in any expected law")

    return result


def find_keyword_in_all_laws(keyword: str, extractions: Dict[str, Dict]) -> List[str]:
    """Find which laws actually contain a keyword."""
    found_in = []
    keyword_lower = keyword.lower()

    for law_code, law_data in extractions.items():
        if " " not in law_code:  # Skip normalized duplicates
            continue
        law_text = get_all_text_from_law(law_data)
        if keyword_lower in law_text:
            found_in.append(law_code)

    return found_in


def run_verification(questions: List[TestQuestion] = None) -> Dict:
    """Run verification on all test questions."""
    if questions is None:
        questions = TEST_QUESTIONS

    extractions = load_all_extractions()
    if not extractions:
        return {"error": "No extractions loaded"}

    print(f"\nVerifying {len(questions)} test questions...")
    print("=" * 70)

    results = []
    valid_count = 0
    invalid_count = 0

    for q in questions:
        result = verify_question(q, extractions)
        results.append(result)

        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1
            print(f"\n[INVALID] {q.id}: {q.query[:50]}...")
            for issue in result["issues"]:
                print(f"  - {issue}")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total questions: {len(questions)}")
    print(f"Valid ground truth: {valid_count} ({valid_count/len(questions):.0%})")
    print(f"Invalid/uncertain: {invalid_count} ({invalid_count/len(questions):.0%})")

    # Find most commonly missing keywords
    all_missing = defaultdict(int)
    for r in results:
        for law, keywords in r["keywords_missing"].items():
            for kw in keywords:
                all_missing[kw] += 1

    if all_missing:
        print(f"\nMost commonly missing keywords:")
        for kw, count in sorted(all_missing.items(), key=lambda x: -x[1])[:10]:
            # Try to find where this keyword actually exists
            found_in = find_keyword_in_all_laws(kw, extractions)
            if found_in:
                print(f"  '{kw}': missing {count}x, but found in: {found_in[:3]}")
            else:
                print(f"  '{kw}': missing {count}x, NOT FOUND in any law")

    return {
        "total": len(questions),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": results
    }


def verify_single_question(question_id: str):
    """Verify a single question and show detailed results."""
    extractions = load_all_extractions()

    question = None
    for q in TEST_QUESTIONS:
        if q.id == question_id:
            question = q
            break

    if question is None:
        print(f"Question {question_id} not found")
        return

    print(f"\nVerifying: {question.id}")
    print(f"Query: {question.query}")
    print(f"Expected laws: {question.expected_laws}")
    print(f"Expected keywords: {question.expected_keywords}")
    print("-" * 60)

    result = verify_question(question, extractions)

    print(f"\nLaws verified: {result['laws_verified']}")
    print(f"Laws missing: {result['laws_missing']}")

    for law, keywords in result["keywords_found"].items():
        print(f"\nIn {law}:")
        print(f"  Found: {keywords}")
        print(f"  Missing: {result['keywords_missing'].get(law, [])}")

    if result["issues"]:
        print(f"\nIssues:")
        for issue in result["issues"]:
            print(f"  - {issue}")

    # For missing keywords, show where they actually exist
    all_missing = set()
    for kws in result["keywords_missing"].values():
        all_missing.update(kws)

    if all_missing:
        print(f"\n\nSearching for missing keywords in ALL laws:")
        for kw in all_missing:
            found_in = find_keyword_in_all_laws(kw, extractions)
            if found_in:
                print(f"  '{kw}' found in: {found_in[:5]}")
            else:
                print(f"  '{kw}' NOT FOUND in any law")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify RAG test ground truth")
    parser.add_argument("--question", "-q", type=str, help="Verify single question by ID")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of questions")

    args = parser.parse_args()

    if args.question:
        verify_single_question(args.question)
    else:
        questions = TEST_QUESTIONS
        if args.limit:
            questions = questions[:args.limit]
        run_verification(questions)
