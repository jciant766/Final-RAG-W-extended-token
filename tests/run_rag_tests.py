"""
RAG Test Runner for Maltese Law System.

Runs test queries against the retrieval system and evaluates:
1. Query expansion (are synonyms being added?)
2. Law retrieval (are expected laws found?)
3. Article retrieval (are specific articles found?)

Usage:
    python tests/run_rag_tests.py
    python tests/run_rag_tests.py --query "orange light"
    python tests/run_rag_tests.py --mode synonym
"""

import sys
import argparse
from pathlib import Path

# Add project root and tests directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from typing import List, Dict, Optional
from src.retrieval.graphrag_retriever import GraphRAGRetriever
from src.retrieval.query_classifier import QueryClassifier, LEGAL_TERM_SYNONYMS
from rag_test_questions import (
    ALL_TEST_QUESTIONS,
    SYNONYM_TESTS,
    HIERARCHICAL_TESTS,
    FailureMode,
    RAGTestQuestion
)


def test_query_expansion(query: str) -> Dict:
    """Test if query expansion works for a given query."""
    classifier = QueryClassifier()
    result = classifier.expand_query(query)

    return {
        "query": query,
        "expanded": result["expanded_query"],
        "terms_added": result.get("terms_added", []),
        "expansions": result.get("expansions", []),
        "success": len(result.get("terms_added", [])) > 0
    }


def test_retrieval(
    query: str,
    expected_laws: List[str] = None,
    expected_articles: List[str] = None,
    retriever: GraphRAGRetriever = None
) -> Dict:
    """
    Test retrieval for a query and check if expected sources are found.

    Returns:
        Dict with retrieval results and success metrics
    """
    if retriever is None:
        retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")

    # Run search
    results = retriever.search(
        query=query,
        limit=15,
        top_laws=25,
        expand_graph=True,
        auto_classify=True
    )

    # Extract found laws and articles
    found_laws = set()
    found_articles = set()

    for law in results.get("laws", []):
        found_laws.add(law.get("law_code", ""))

    for article in results.get("articles", []):
        law_code = article.get("law_code", "")
        art_num = article.get("article_number", "")
        found_laws.add(law_code)
        found_articles.add(f"{law_code} Art. {art_num}")

    for article in results.get("related_articles", []):
        law_code = article.get("law_code", "")
        art_num = article.get("article_number", "")
        found_laws.add(law_code)
        found_articles.add(f"{law_code} Art. {art_num}")

    # Calculate metrics
    expected_laws = expected_laws or []
    expected_articles = expected_articles or []

    laws_found = [law for law in expected_laws if any(law in fl for fl in found_laws)]
    laws_missed = [law for law in expected_laws if not any(law in fl for fl in found_laws)]

    # Recall: what percentage of expected items were found?
    law_recall = len(laws_found) / len(expected_laws) if expected_laws else 1.0

    return {
        "query": query,
        "query_expansion": results.get("query_expansion"),
        "classification": results.get("classification"),
        "categories_used": results.get("categories_used", []),
        "laws_searched": results.get("laws_searched", []),
        "found_laws": list(found_laws),
        "found_articles": list(found_articles)[:10],  # Limit for display
        "expected_laws": expected_laws,
        "laws_found": laws_found,
        "laws_missed": laws_missed,
        "law_recall": law_recall,
        "articles_count": len(results.get("articles", [])),
        "related_count": len(results.get("related_articles", [])),
        "success": law_recall >= 0.5  # At least 50% of expected laws found
    }


def run_test_question(test: RAGTestQuestion, retriever: GraphRAGRetriever = None) -> Dict:
    """Run a single test question and return results."""
    print(f"\n{'='*60}")
    print(f"[{test.id}] {test.query}")
    print(f"Expected laws: {', '.join(test.expected_laws)}")
    print(f"Failure mode: {test.failure_mode.value}")
    print("-" * 60)

    # Test query expansion first
    expansion = test_query_expansion(test.query)
    if expansion["success"]:
        print(f"✓ Query expanded: {expansion['terms_added']}")
    else:
        print(f"✗ No query expansion")

    # Test retrieval
    result = test_retrieval(
        query=test.query,
        expected_laws=test.expected_laws,
        expected_articles=test.expected_articles,
        retriever=retriever
    )

    # Report results
    if result["laws_found"]:
        print(f"✓ Found: {', '.join(result['laws_found'])}")
    if result["laws_missed"]:
        print(f"✗ Missed: {', '.join(result['laws_missed'])}")

    print(f"  Categories: {result['categories_used']}")
    print(f"  Laws searched: {len(result['laws_searched'])}")
    print(f"  Articles found: {result['articles_count']}")
    print(f"  Law recall: {result['law_recall']:.1%}")

    return {
        "test": test,
        "expansion": expansion,
        "retrieval": result,
        "passed": result["success"]
    }


def run_all_tests(mode: str = "all", retriever: GraphRAGRetriever = None) -> Dict:
    """
    Run all test questions or a specific subset.

    Args:
        mode: "all", "synonym", "hierarchical", "cross_ref", etc.
        retriever: Optional shared retriever instance
    """
    if retriever is None:
        print("Initializing retriever...")
        retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")

    # Select tests based on mode
    if mode == "all":
        tests = ALL_TEST_QUESTIONS
    elif mode == "synonym":
        tests = SYNONYM_TESTS
    elif mode == "hierarchical":
        tests = HIERARCHICAL_TESTS
    else:
        tests = [t for t in ALL_TEST_QUESTIONS if t.failure_mode.value == mode]

    print(f"\nRunning {len(tests)} tests (mode: {mode})")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for test in tests:
        result = run_test_question(test, retriever)
        results.append(result)
        if result["passed"]:
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed}")
    print(f"Pass rate: {passed/len(tests):.1%}")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - [{r['test'].id}] {r['test'].query}")
                print(f"    Missed: {r['retrieval']['laws_missed']}")

    return {
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(tests) if tests else 0,
        "results": results
    }


def test_single_query(query: str) -> None:
    """Test a single query interactively."""
    print(f"\nTesting: {query}")
    print("=" * 60)

    # Test expansion
    print("\n1. QUERY EXPANSION")
    print("-" * 40)
    expansion = test_query_expansion(query)
    print(f"Original: {expansion['query']}")
    print(f"Expanded: {expansion['expanded']}")
    if expansion["terms_added"]:
        print(f"Terms added: {expansion['terms_added']}")
    else:
        print("(No expansion - term not in synonym dictionary)")

    # Test retrieval
    print("\n2. RETRIEVAL")
    print("-" * 40)
    result = test_retrieval(query)

    print(f"Classification: {result.get('classification', {}).get('categories', [])}")
    print(f"Categories used: {result['categories_used']}")
    print(f"Laws searched: {len(result['laws_searched'])} laws")
    print(f"Articles found: {result['articles_count']}")
    print(f"Related (via graph): {result['related_count']}")

    if result["found_laws"]:
        print(f"\nLaws found:")
        for law in sorted(result["found_laws"])[:10]:
            print(f"  - {law}")

    if result["found_articles"]:
        print(f"\nTop articles:")
        for art in result["found_articles"][:5]:
            print(f"  - {art}")


def show_synonym_coverage():
    """Show which synonyms are covered in the dictionary."""
    print("\nLEGAL SYNONYM DICTIONARY COVERAGE")
    print("=" * 60)

    categories = {
        "Traffic/Transport": ["orange light", "yellow light", "amber light", "drunk driving",
                             "speeding", "red light", "jaywalking", "traffic ticket", "parking ticket"],
        "Time/Prescription": ["statute of limitations", "time limit", "deadline", "limitation period"],
        "Liability": ["medical malpractice", "malpractice", "negligence", "damages", "liability", "sue"],
        "Criminal": ["crime", "punishment", "imprisonment", "bail", "theft", "murder", "assault", "robbery", "fraud"],
        "Employment": ["fire", "fired", "quit", "wages", "minimum wage"],
        "Property": ["evict", "landlord", "tenant", "rent", "deposit", "ownership", "mortgage"],
        "Corporate": ["director", "shareholder", "bankruptcy"],
        "Family": ["divorce", "custody", "alimony", "inheritance"],
    }

    for category, terms in categories.items():
        print(f"\n{category}:")
        for term in terms:
            if term in LEGAL_TERM_SYNONYMS:
                synonyms = LEGAL_TERM_SYNONYMS[term][:3]  # Show first 3
                print(f"  ✓ {term} → {', '.join(synonyms)}")
            else:
                print(f"  ✗ {term} (not covered)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Maltese Law RAG system")
    parser.add_argument("--query", "-q", type=str, help="Test a single query")
    parser.add_argument("--mode", "-m", type=str, default="synonym",
                       choices=["all", "synonym", "hierarchical", "cross_reference",
                               "schedule_appendix", "multi_hop", "abbreviation"],
                       help="Test mode/category")
    parser.add_argument("--synonyms", "-s", action="store_true",
                       help="Show synonym dictionary coverage")

    args = parser.parse_args()

    if args.synonyms:
        show_synonym_coverage()
    elif args.query:
        test_single_query(args.query)
    else:
        run_all_tests(mode=args.mode)
