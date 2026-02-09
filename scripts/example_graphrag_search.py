#!/usr/bin/env python3
"""
Example usage of the Graph RAG retriever for Maltese Laws.

This demonstrates:
1. Basic semantic search
2. Category filtering
3. Graph traversal (finding related articles via cross-references)
4. Building RAG context for LLM

Run after ingestion:
    python scripts/ingest_json_extractions.py extractions/ --overwrite
    python scripts/example_graphrag_search.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.graphrag_retriever import GraphRAGRetriever, build_rag_context


def main():
    print("=" * 60)
    print("Graph RAG Search Demo - Maltese Laws")
    print("=" * 60)
    print("3-STAGE HIERARCHICAL FILTERING PIPELINE")
    print("1. Query Classification (LLM)")
    print("2. Category Pre-filtering")
    print("3. Semantic Search within filtered laws")
    print("=" * 60)

    # Initialize retriever
    print("\nConnecting to database...")
    try:
        retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
    except ValueError as e:
        print(f"Error: {e}")
        print("Run ingestion first: python scripts/ingest_json_extractions.py extractions/")
        return

    # Show database stats
    counts = retriever.count()
    print(f"\nDatabase contents:")
    for table, count in counts.items():
        print(f"  - {table}: {count:,}")

    # Example 1: Full 3-stage pipeline
    print("\n" + "-" * 60)
    print("Example 1: Full 3-Stage Pipeline (Classification -> Filter -> Search)")
    print("-" * 60)

    query = "What are the penalties for tax evasion?"
    print(f"Query: {query}\n")

    results = retriever.search(
        query=query,
        limit=5,
        expand_graph=True,
        max_hops=1,
        use_hierarchical=True,
        auto_classify=True,  # NEW: LLM classifies query into categories first
        top_laws=10
    )

    # Show classification results
    if results.get('classification'):
        print("STAGE 1 - QUERY CLASSIFICATION:")
        classification = results['classification']
        print(f"  Categories: {classification.get('categories', [])}")
        print(f"  Confidence: {classification.get('confidence', {})}")
        print(f"  Reasoning: {classification.get('reasoning', '')}")

    if results.get('categories_used'):
        print(f"\nSTAGE 2 - CATEGORY PRE-FILTER:")
        print(f"  Filtering laws by: {results['categories_used']}")
        print(f"  (This removes irrelevant domains BEFORE semantic search)")

    # Show which laws were identified as relevant
    if results['laws_searched']:
        print(f"\nSTAGE 3 - HIERARCHICAL LAW SEARCH:")
        print(f"  Found {len(results['laws_searched'])} relevant laws:")
        for law_code in results['laws_searched'][:5]:
            law_info = next((l for l in results['laws'] if l['law_code'] == law_code), None)
            if law_info:
                print(f"    - {law_code}: {law_info['law_name'][:50]}...")
            else:
                print(f"    - {law_code}")
        if len(results['laws_searched']) > 5:
            print(f"    ... and {len(results['laws_searched']) - 5} more")

    print(f"\nSTAGE 4 - ARTICLE SEARCH:")
    print(f"  Found {len(results['articles'])} primary articles")
    print(f"  (Searched ONLY within {len(results['laws_searched'])} laws, not all 60k articles!)")

    if results['articles']:
        print("\n  Top article:")
        article = results['articles'][0]
        print(f"    ID: {article['id']}")
        print(f"    Law: {article['law_code']} - {article['law_name']}")
        print(f"    Article: {article['article_number']}")
        if article.get('title'):
            print(f"    Title: {article['title']}")
        print(f"    Text preview: {article['text'][:200]}...")

    if results['related_articles']:
        print(f"\nSTAGE 5 - GRAPH EXPANSION:")
        print(f"  Found {len(results['related_articles'])} related articles via cross-references")

    if results['graph_path']:
        print("  Traversal paths:")
        for path in results['graph_path'][:3]:
            print(f"    {path['from']} --[{path['type']}]--> {path['to']}")

    # Example 2: Category filtered search
    print("\n" + "-" * 60)
    print("Example 2: Search with category filter")
    print("-" * 60)

    query = "criminal penalties"
    categories = ["criminal_law"]
    print(f"Query: {query}")
    print(f"Categories: {categories}\n")

    results = retriever.search(
        query=query,
        limit=5,
        categories=categories,
        expand_graph=False
    )

    print(f"Found {len(results['articles'])} articles in criminal_law category")

    if results['articles']:
        for i, article in enumerate(results['articles'][:3], 1):
            print(f"\n  {i}. {article['law_code']}, Article {article['article_number']}")
            if article.get('title'):
                print(f"     Title: {article['title']}")

    # Example 3: Search within specific law
    print("\n" + "-" * 60)
    print("Example 3: Search within specific law")
    print("-" * 60)

    query = "jurisdiction"
    law_filter = "Cap. 1"
    print(f"Query: {query}")
    print(f"Law filter: {law_filter}\n")

    results = retriever.search(
        query=query,
        limit=10,
        law_filter=law_filter
    )

    print(f"Found {len(results['articles'])} articles in {law_filter}")

    for article in results['articles']:
        print(f"  - Article {article['article_number']}: {article.get('title', 'No title')}")

    # Example 4: Get related articles via edges
    print("\n" + "-" * 60)
    print("Example 4: Find articles related to a specific article")
    print("-" * 60)

    if results['articles']:
        source_article = results['articles'][0]
        print(f"Finding articles related to: {source_article['id']}\n")

        related = retriever.get_related_articles(source_article['id'])

        if related:
            print(f"Found {len(related)} related articles:")
            for article in related[:5]:
                print(f"  --[{article['edge_type']}]--> {article['id']}")
                print(f"     {article['law_code']}, Article {article['article_number']}")
        else:
            print("No related articles found (this article has no cross-references)")

    # Example 5: Build RAG context for LLM
    print("\n" + "-" * 60)
    print("Example 5: Build RAG context for LLM")
    print("-" * 60)

    query = "What is the jurisdiction of ecclesiastical courts?"
    print(f"Query: {query}\n")

    results = retriever.search(query=query, limit=3, expand_graph=True)
    context = build_rag_context(results, max_articles=3)

    print("Generated context (first 1000 chars):")
    print("-" * 40)
    print(context[:1000])
    if len(context) > 1000:
        print(f"\n... ({len(context) - 1000} more characters)")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
