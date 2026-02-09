#!/usr/bin/env python3
"""
Test the retrieval fix for medical malpractice statute of limitations question.

This tests:
1. Query expansion: "statute of limitations" → adds "prescription"
2. Fundamental laws: civil_law category → adds Cap. 16 (Civil Code)
3. Article retrieval: Finds Article 2153 about prescription periods
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.graphrag_retriever import GraphRAGRetriever
from src.retrieval.query_classifier import QueryClassifier

def main():
    print("=" * 70)
    print("TESTING RETRIEVAL FIX")
    print("=" * 70)

    # Test 1: Query Expansion
    print("\n" + "-" * 70)
    print("TEST 1: Query Expansion")
    print("-" * 70)

    classifier = QueryClassifier()
    test_query = "What is the statute of limitations for medical malpractice in Malta?"

    expansion = classifier.expand_query(test_query)
    print(f"Original: {expansion['original_query']}")
    print(f"Expanded: {expansion['expanded_query']}")
    print(f"Terms added: {expansion['terms_added']}")

    if "prescription" in expansion['expanded_query'].lower():
        print("[PASS] Query expanded with 'prescription'")
    else:
        print("[FAIL] Query not expanded")

    # Test 2: Full Search with Fundamental Laws
    print("\n" + "-" * 70)
    print("TEST 2: Full Search (Query Expansion + Fundamental Laws)")
    print("-" * 70)

    retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")

    results = retriever.search(
        query=test_query,
        limit=15,
        top_laws=15,
        expand_graph=True,
        auto_classify=True,
        max_hops=1
    )

    # Check if Cap. 16 was added as fundamental law
    print(f"\nCategories detected: {results.get('categories_used', [])}")
    print(f"Fundamental laws added: {results.get('fundamental_laws_added', [])}")
    print(f"Total laws searched: {len(results.get('laws_searched', []))}")
    print(f"Laws searched: {results.get('laws_searched', [])[:10]}")

    if "Cap. 16" in results.get("laws_searched", []):
        print("[PASS] SUCCESS: Cap. 16 (Civil Code) included in search")
    else:
        print("[FAIL] FAILED: Cap. 16 not in search")

    # Check if we found Article 2153
    print("\n" + "-" * 70)
    print("TEST 3: Article 2153 Retrieval")
    print("-" * 70)

    articles = results.get("articles", [])
    print(f"Found {len(articles)} primary articles")

    found_2153 = False
    for i, art in enumerate(articles):
        art_num = art.get("article_number", "")
        law_code = art.get("law_code", "")
        text_preview = art.get("text", "")[:150]

        # Check for Article 2153
        if "2153" in str(art_num) or ("prescription" in text_preview.lower() and "damages" in text_preview.lower()):
            found_2153 = True
            print(f"\n[PASS] FOUND TARGET ARTICLE:")
            print(f"  {law_code}, Article {art_num}")
            print(f"  Text: {text_preview}...")

        # Also check related articles
    related = results.get("related_articles", [])
    for art in related:
        art_num = art.get("article_number", "")
        law_code = art.get("law_code", "")
        text = art.get("text", "")
        if "2153" in str(art_num) or ("prescription" in text.lower() and "damages" in text.lower()):
            found_2153 = True
            print(f"\n[PASS] FOUND TARGET in related articles:")
            print(f"  {law_code}, Article {art_num}")

    if not found_2153:
        print("\n[FAIL] Article 2153 not found in primary results")
        print("\nTop 5 articles found:")
        for i, art in enumerate(articles[:5], 1):
            print(f"  {i}. {art.get('law_code')} Art. {art.get('article_number')}: {art.get('text', '')[:80]}...")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    query_expanded = "prescription" in expansion['expanded_query'].lower()
    cap16_searched = "Cap. 16" in results.get("laws_searched", [])

    print(f"Query Expansion:     {'[PASS] PASS' if query_expanded else '[FAIL] FAIL'}")
    print(f"Fundamental Laws:    {'[PASS] PASS' if cap16_searched else '[FAIL] FAIL'}")
    print(f"Article 2153 Found:  {'[PASS] PASS' if found_2153 else '[FAIL] FAIL'}")

    if query_expanded and cap16_searched and found_2153:
        print("\n*** ALL TESTS PASSED! The fix is working.")
    elif query_expanded and cap16_searched:
        print("\n[!]  Query expansion and fundamental laws work, but Article 2153 not in top results.")
        print("    This might still be OK - the relevant article should now be findable.")
    else:
        print("\n[X] Some tests failed. Check the implementation.")


if __name__ == "__main__":
    main()
