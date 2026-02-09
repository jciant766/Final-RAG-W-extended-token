#!/usr/bin/env python3
"""
100 Question Validation Suite for Maltese Law RAG.

Tests retrieval quality across all legal domains with real lawyer-style questions.
Validates that retrieved articles actually answer the questions.
"""

import sys
from pathlib import Path
import json
import time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.graphrag_retriever import GraphRAGRetriever
from src.retrieval.query_classifier import QueryClassifier

# =============================================================================
# 100 LEGAL QUESTIONS - Organized by Domain
# =============================================================================
QUESTIONS = [
    # =========================================================================
    # CIVIL LAW (15 questions)
    # =========================================================================
    {"id": 1, "domain": "civil_law", "question": "What is the prescription period for claiming damages from a car accident?"},
    {"id": 2, "domain": "civil_law", "question": "How long do I have to sue for breach of contract?"},
    {"id": 3, "domain": "civil_law", "question": "What are the essential elements of a valid contract under Maltese law?"},
    {"id": 4, "domain": "civil_law", "question": "Can a minor enter into a binding contract?"},
    {"id": 5, "domain": "civil_law", "question": "What is the difference between nullity and rescission of a contract?"},
    {"id": 6, "domain": "civil_law", "question": "How is compensation for moral damages calculated?"},
    {"id": 7, "domain": "civil_law", "question": "What is the prescription period for debt recovery?"},
    {"id": 8, "domain": "civil_law", "question": "Can I claim damages for defamation?"},
    {"id": 9, "domain": "civil_law", "question": "What is the liability of a guardian for acts of a minor?"},
    {"id": 10, "domain": "civil_law", "question": "How does joint and several liability work?"},
    {"id": 11, "domain": "civil_law", "question": "What is the effect of force majeure on contractual obligations?"},
    {"id": 12, "domain": "civil_law", "question": "How are interest rates on debts regulated?"},
    {"id": 13, "domain": "civil_law", "question": "What is the warranty period for defective goods?"},
    {"id": 14, "domain": "civil_law", "question": "Can I transfer my contractual rights to another person?"},
    {"id": 15, "domain": "civil_law", "question": "What remedies exist for unjust enrichment?"},

    # =========================================================================
    # CRIMINAL LAW (15 questions)
    # =========================================================================
    {"id": 16, "domain": "criminal_law", "question": "What types of punishments exist under Maltese criminal law?"},
    {"id": 17, "domain": "criminal_law", "question": "How does a suspended sentence work?"},
    {"id": 18, "domain": "criminal_law", "question": "What is the minimum age of criminal responsibility?"},
    {"id": 19, "domain": "criminal_law", "question": "Can a company be criminally liable?"},
    {"id": 20, "domain": "criminal_law", "question": "What are the rules for concurrent sentences?"},
    {"id": 21, "domain": "criminal_law", "question": "How is compensation to crime victims determined?"},
    {"id": 22, "domain": "criminal_law", "question": "What is the difference between a crime and a contravention?"},
    {"id": 23, "domain": "criminal_law", "question": "When can property be forfeited in criminal proceedings?"},
    {"id": 24, "domain": "criminal_law", "question": "What are the rules for recidivists?"},
    {"id": 25, "domain": "criminal_law", "question": "How long can someone be detained before trial?"},
    {"id": 26, "domain": "criminal_law", "question": "What is the procedure for issuing an arrest warrant?"},
    {"id": 27, "domain": "criminal_law", "question": "Can I get bail for serious offences?"},
    {"id": 28, "domain": "criminal_law", "question": "What is the penalty for perjury?"},
    {"id": 29, "domain": "criminal_law", "question": "How are fines calculated in criminal cases?"},
    {"id": 30, "domain": "criminal_law", "question": "What is the statute of limitations for criminal offences?"},

    # =========================================================================
    # COMPANY LAW (12 questions)
    # =========================================================================
    {"id": 31, "domain": "company_law", "question": "What is the minimum share capital for a private limited company?"},
    {"id": 32, "domain": "company_law", "question": "What are the duties of company directors?"},
    {"id": 33, "domain": "company_law", "question": "How many directors must a private company have?"},
    {"id": 34, "domain": "company_law", "question": "What happens if a company fails to file annual returns?"},
    {"id": 35, "domain": "company_law", "question": "Can a director be personally liable for company debts?"},
    {"id": 36, "domain": "company_law", "question": "What are the grounds for winding up a company?"},
    {"id": 37, "domain": "company_law", "question": "How do shareholders approve major transactions?"},
    {"id": 38, "domain": "company_law", "question": "What are the requirements for a company name?"},
    {"id": 39, "domain": "company_law", "question": "How can minority shareholders protect their rights?"},
    {"id": 40, "domain": "company_law", "question": "What is the procedure for changing a company's memorandum?"},
    {"id": 41, "domain": "company_law", "question": "Can a company buy back its own shares?"},
    {"id": 42, "domain": "company_law", "question": "What are the rules for dividend distribution?"},

    # =========================================================================
    # EMPLOYMENT LAW (12 questions)
    # =========================================================================
    {"id": 43, "domain": "employment_law", "question": "What is the minimum notice period for terminating employment?"},
    {"id": 44, "domain": "employment_law", "question": "How many hours per week is the maximum working time?"},
    {"id": 45, "domain": "employment_law", "question": "What is the minimum wage in Malta?"},
    {"id": 46, "domain": "employment_law", "question": "How much annual leave is an employee entitled to?"},
    {"id": 47, "domain": "employment_law", "question": "What constitutes unfair dismissal?"},
    {"id": 48, "domain": "employment_law", "question": "Can an employer change the terms of employment unilaterally?"},
    {"id": 49, "domain": "employment_law", "question": "What are the rules for probationary periods?"},
    {"id": 50, "domain": "employment_law", "question": "How is redundancy compensation calculated?"},
    {"id": 51, "domain": "employment_law", "question": "What are the maternity leave entitlements?"},
    {"id": 52, "domain": "employment_law", "question": "Can an employer monitor employee emails?"},
    {"id": 53, "domain": "employment_law", "question": "What is the procedure for collective redundancies?"},
    {"id": 54, "domain": "employment_law", "question": "Are non-compete clauses enforceable in Malta?"},

    # =========================================================================
    # PROPERTY LAW (10 questions)
    # =========================================================================
    {"id": 55, "domain": "property_law", "question": "How is ownership of immovable property transferred?"},
    {"id": 56, "domain": "property_law", "question": "What are the rights of a tenant under a lease agreement?"},
    {"id": 57, "domain": "property_law", "question": "How do easements work under Maltese law?"},
    {"id": 58, "domain": "property_law", "question": "What is the prescription period for acquiring ownership by possession?"},
    {"id": 59, "domain": "property_law", "question": "Can a landlord evict a tenant without a court order?"},
    {"id": 60, "domain": "property_law", "question": "What are the co-owners' rights in jointly owned property?"},
    {"id": 61, "domain": "property_law", "question": "How is a mortgage registered?"},
    {"id": 62, "domain": "property_law", "question": "What taxes apply to property transfers?"},
    {"id": 63, "domain": "property_law", "question": "Can agricultural land be converted to residential use?"},
    {"id": 64, "domain": "property_law", "question": "What happens to a lease when the property is sold?"},

    # =========================================================================
    # FAMILY LAW (10 questions)
    # =========================================================================
    {"id": 65, "domain": "family_law", "question": "What are the grounds for divorce in Malta?"},
    {"id": 66, "domain": "family_law", "question": "How is child custody determined?"},
    {"id": 67, "domain": "family_law", "question": "What is the waiting period before remarriage after divorce?"},
    {"id": 68, "domain": "family_law", "question": "How is maintenance calculated after divorce?"},
    {"id": 69, "domain": "family_law", "question": "What are the rules for prenuptial agreements?"},
    {"id": 70, "domain": "family_law", "question": "How does intestate succession work?"},
    {"id": 71, "domain": "family_law", "question": "Can children inherit from their unmarried father?"},
    {"id": 72, "domain": "family_law", "question": "What is the legitimate portion in inheritance law?"},
    {"id": 73, "domain": "family_law", "question": "How are matrimonial assets divided on divorce?"},
    {"id": 74, "domain": "family_law", "question": "What are the requirements for a valid will?"},

    # =========================================================================
    # TAX LAW (8 questions)
    # =========================================================================
    {"id": 75, "domain": "tax_law", "question": "What is the income tax rate for individuals?"},
    {"id": 76, "domain": "tax_law", "question": "What are the penalties for late tax filing?"},
    {"id": 77, "domain": "tax_law", "question": "How are capital gains taxed in Malta?"},
    {"id": 78, "domain": "tax_law", "question": "What is the VAT rate in Malta?"},
    {"id": 79, "domain": "tax_law", "question": "Are there tax incentives for startups?"},
    {"id": 80, "domain": "tax_law", "question": "How does the tax refund system for shareholders work?"},
    {"id": 81, "domain": "tax_law", "question": "What expenses are tax deductible for companies?"},
    {"id": 82, "domain": "tax_law", "question": "How are rental income taxed?"},

    # =========================================================================
    # CONSTITUTIONAL LAW (5 questions)
    # =========================================================================
    {"id": 83, "domain": "constitutional_law", "question": "What are the fundamental human rights in the Constitution?"},
    {"id": 84, "domain": "constitutional_law", "question": "How is the President of Malta elected?"},
    {"id": 85, "domain": "constitutional_law", "question": "What powers does the Constitutional Court have?"},
    {"id": 86, "domain": "constitutional_law", "question": "Can fundamental rights be limited?"},
    {"id": 87, "domain": "constitutional_law", "question": "What is the procedure for amending the Constitution?"},

    # =========================================================================
    # ADMINISTRATIVE LAW (5 questions)
    # =========================================================================
    {"id": 88, "domain": "administrative_law", "question": "How do I appeal a government administrative decision?"},
    {"id": 89, "domain": "administrative_law", "question": "What is the time limit for filing an administrative appeal?"},
    {"id": 90, "domain": "administrative_law", "question": "Can government decisions be reviewed by courts?"},
    {"id": 91, "domain": "administrative_law", "question": "What are the grounds for judicial review?"},
    {"id": 92, "domain": "administrative_law", "question": "How do I obtain information from government under FOI?"},

    # =========================================================================
    # CONSUMER PROTECTION (4 questions)
    # =========================================================================
    {"id": 93, "domain": "consumer_protection_law", "question": "What is the return period for online purchases?"},
    {"id": 94, "domain": "consumer_protection_law", "question": "What warranties apply to consumer goods?"},
    {"id": 95, "domain": "consumer_protection_law", "question": "Can a business exclude liability for defective products?"},
    {"id": 96, "domain": "consumer_protection_law", "question": "How do I file a complaint against a trader?"},

    # =========================================================================
    # DATA PROTECTION (4 questions)
    # =========================================================================
    {"id": 97, "domain": "data_protection_and_privacy", "question": "What are my rights under GDPR in Malta?"},
    {"id": 98, "domain": "data_protection_and_privacy", "question": "What is the penalty for data breaches?"},
    {"id": 99, "domain": "data_protection_and_privacy", "question": "How long can a company retain my personal data?"},
    {"id": 100, "domain": "data_protection_and_privacy", "question": "Do I have the right to be forgotten?"},
]


def run_validation(output_file: str = None):
    """Run the 100 question validation."""
    print("=" * 80)
    print("100 QUESTION VALIDATION SUITE - MALTESE LAW RAG")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total questions: {len(QUESTIONS)}")
    print("=" * 80)

    retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
    classifier = QueryClassifier()

    results = []
    domain_stats = {}
    total_time = 0

    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i:3d}/100] {q['domain'].upper()}")
        print(f"Q: {q['question']}")

        start = time.time()

        # Get query expansion
        expansion = classifier.expand_query(q['question'])

        # Run search
        search_results = retriever.search(
            query=q['question'],
            limit=10,
            top_laws=15,
            expand_graph=True,
            auto_classify=True,
            max_hops=1
        )

        elapsed = time.time() - start
        total_time += elapsed

        # Extract key info
        articles = search_results.get('articles', [])
        categories = search_results.get('categories_used', [])
        laws_searched = search_results.get('laws_searched', [])
        fundamental_added = search_results.get('fundamental_laws_added', [])
        terms_added = expansion.get('terms_added', [])

        # Build result record
        result = {
            "id": q['id'],
            "domain": q['domain'],
            "question": q['question'],
            "categories_detected": categories,
            "query_expansion": terms_added[:3] if terms_added else [],
            "fundamental_laws_added": fundamental_added,
            "laws_searched_count": len(laws_searched),
            "articles_found": len(articles),
            "top_articles": [],
            "elapsed_seconds": round(elapsed, 2)
        }

        # Capture top 3 articles
        for art in articles[:3]:
            result["top_articles"].append({
                "law_code": art.get('law_code'),
                "article_number": art.get('article_number'),
                "title": art.get('title', ''),
                "text_preview": art.get('text', '')[:200]
            })

        results.append(result)

        # Print summary
        print(f"   Categories: {categories}")
        if terms_added:
            print(f"   Expanded: +{terms_added[:3]}")
        print(f"   Laws: {len(laws_searched)} | Articles: {len(articles)} | Time: {elapsed:.2f}s")

        if articles:
            top = articles[0]
            print(f"   Top: {top.get('law_code')} Art. {top.get('article_number')}")

        # Update domain stats
        if q['domain'] not in domain_stats:
            domain_stats[q['domain']] = {"count": 0, "total_articles": 0, "total_time": 0}
        domain_stats[q['domain']]["count"] += 1
        domain_stats[q['domain']]["total_articles"] += len(articles)
        domain_stats[q['domain']]["total_time"] += elapsed

    # Generate summary report
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    print(f"\nTotal questions: {len(QUESTIONS)}")
    print(f"Total time: {total_time:.1f}s ({total_time/len(QUESTIONS):.2f}s avg)")

    print("\nBy Domain:")
    print("-" * 60)
    for domain, stats in sorted(domain_stats.items()):
        avg_articles = stats["total_articles"] / stats["count"]
        avg_time = stats["total_time"] / stats["count"]
        print(f"  {domain:30s}: {stats['count']:3d} q | {avg_articles:.1f} avg articles | {avg_time:.2f}s avg")

    # Count questions with results
    questions_with_results = sum(1 for r in results if r["articles_found"] > 0)
    coverage = questions_with_results / len(results) * 100

    print(f"\nCoverage: {questions_with_results}/{len(results)} questions returned articles ({coverage:.1f}%)")

    # Save detailed results
    if output_file is None:
        output_file = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_path = Path(__file__).parent / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_questions": len(QUESTIONS),
                "total_time_seconds": round(total_time, 2),
                "coverage_percent": round(coverage, 1)
            },
            "domain_stats": domain_stats,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {output_path}")
    print("=" * 80)

    return results, domain_stats


def analyze_results(results_file: str):
    """Analyze saved results and generate a report."""
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    results = data['results']

    # Questions with no results
    no_results = [r for r in results if r['articles_found'] == 0]
    print(f"\nQuestions with NO articles found ({len(no_results)}):")
    for r in no_results:
        print(f"  [{r['id']}] {r['question']}")

    # Questions with query expansion
    with_expansion = [r for r in results if r['query_expansion']]
    print(f"\nQuestions with query expansion ({len(with_expansion)}):")
    for r in with_expansion[:10]:
        print(f"  [{r['id']}] {r['question'][:50]}... -> +{r['query_expansion']}")

    # Questions with fundamental laws added
    with_fundamental = [r for r in results if r['fundamental_laws_added']]
    print(f"\nQuestions with fundamental laws added ({len(with_fundamental)}):")
    for r in with_fundamental[:10]:
        print(f"  [{r['id']}] +{r['fundamental_laws_added']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="100 Question Validation Suite")
    parser.add_argument("--analyze", type=str, help="Analyze existing results file")
    parser.add_argument("--output", type=str, default=None, help="Output filename")

    args = parser.parse_args()

    if args.analyze:
        analyze_results(args.analyze)
    else:
        run_validation(args.output)
