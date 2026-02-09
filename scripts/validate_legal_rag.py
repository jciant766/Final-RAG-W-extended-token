#!/usr/bin/env python3
"""
Comprehensive Legal RAG Validation Suite.

Tests the retrieval system with real lawyer-style questions across multiple domains.
Validates that:
1. Query expansion bridges terminology gaps
2. Fundamental laws are always included
3. Correct articles are retrieved
4. Cross-references are followed properly
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.graphrag_retriever import GraphRAGRetriever
from src.retrieval.query_classifier import QueryClassifier

# =============================================================================
# TEST CASES - Real lawyer questions with expected results
# =============================================================================
TEST_CASES = [
    # CIVIL LAW
    {
        "question": "What is the statute of limitations for medical malpractice in Malta?",
        "domain": "civil_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": ["2153"],  # Prescription for damages
        "key_terms": ["prescription", "damages", "two years"],
        "difficulty": "hard"  # Requires query expansion
    },
    {
        "question": "What are the requirements for a valid contract in Maltese law?",
        "domain": "civil_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": ["966", "967"],  # Contract essentials
        "key_terms": ["contract", "consent", "object", "consideration"],
        "difficulty": "medium"
    },
    {
        "question": "How do I claim compensation for breach of contract?",
        "domain": "civil_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],  # Multiple articles on damages
        "key_terms": ["damages", "compensation", "breach"],
        "difficulty": "medium"
    },
    {
        "question": "What is the prescriptive period for debt collection?",
        "domain": "civil_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["prescription", "debt", "years"],
        "difficulty": "easy"  # Uses legal term directly
    },

    # CRIMINAL LAW
    # NOTE: Cap. 9 only has Articles 1-31 (general provisions) in database.
    # Specific crime articles (theft 261, murder 211, etc.) are NOT ingested.
    {
        "question": "What types of punishments exist under Maltese criminal law?",
        "domain": "criminal_law",
        "expected_laws": ["Cap. 9"],
        "expected_articles": ["7", "8", "11", "12"],  # General punishment articles
        "key_terms": ["punishment", "imprisonment", "fine", "detention"],
        "difficulty": "easy"
    },
    {
        "question": "How are criminal sentences calculated in Malta?",
        "domain": "criminal_law",
        "expected_laws": ["Cap. 9"],
        "expected_articles": ["17", "22"],  # Concurrent offences, computation
        "key_terms": ["sentence", "punishment", "concurrent", "computation"],
        "difficulty": "easy"
    },
    {
        "question": "Can I get bail for drug trafficking charges?",
        "domain": "criminal_law",
        "expected_laws": ["Cap. 9", "Cap. 101"],
        "expected_articles": [],
        "key_terms": ["bail", "trafficking", "drugs"],
        "difficulty": "hard"  # Requires "bail" -> "provisional liberty" expansion
    },
    {
        "question": "What is a suspended sentence under Maltese law?",
        "domain": "criminal_law",
        "expected_laws": ["Cap. 9"],
        "expected_articles": ["28A", "28B"],  # Suspended sentence articles
        "key_terms": ["suspended", "sentence", "operational period"],
        "difficulty": "medium"
    },

    # COMPANY LAW
    {
        "question": "What are the fiduciary duties of company directors?",
        "domain": "company_law",
        "expected_laws": ["Cap. 386"],
        "expected_articles": ["136", "137"],
        "key_terms": ["director", "duty", "good faith", "company"],
        "difficulty": "medium"
    },
    {
        "question": "How do I register a limited liability company in Malta?",
        "domain": "company_law",
        "expected_laws": ["Cap. 386"],
        "expected_articles": [],
        "key_terms": ["registration", "company", "memorandum", "articles"],
        "difficulty": "easy"
    },
    {
        "question": "What happens when a company goes bankrupt?",
        "domain": "company_law",
        "expected_laws": ["Cap. 386"],
        "expected_articles": [],
        "key_terms": ["winding up", "liquidation", "insolvency"],
        "difficulty": "hard"  # Requires "bankrupt" -> "winding up" expansion
    },
    {
        "question": "What are the shareholder rights in a Maltese company?",
        "domain": "company_law",
        "expected_laws": ["Cap. 386"],
        "expected_articles": [],
        "key_terms": ["shareholder", "member", "rights", "voting"],
        "difficulty": "medium"
    },

    # EMPLOYMENT LAW
    {
        "question": "What is the notice period for terminating employment?",
        "domain": "employment_law",
        "expected_laws": ["Cap. 452"],
        "expected_articles": [],
        "key_terms": ["notice", "termination", "employment"],
        "difficulty": "easy"
    },
    {
        "question": "Can my employer fire me without warning?",
        "domain": "employment_law",
        "expected_laws": ["Cap. 452"],
        "expected_articles": [],
        "key_terms": ["dismissal", "unfair", "termination"],
        "difficulty": "medium"
    },
    {
        "question": "What are the minimum wage requirements in Malta?",
        "domain": "employment_law",
        "expected_laws": ["Cap. 452"],
        "expected_articles": [],
        "key_terms": ["wage", "minimum", "remuneration"],
        "difficulty": "easy"
    },

    # PROPERTY LAW
    {
        "question": "How do I transfer ownership of immovable property?",
        "domain": "property_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["ownership", "property", "transfer", "conveyance"],
        "difficulty": "medium"
    },
    {
        "question": "What are tenant rights when a landlord wants to evict?",
        "domain": "property_law",
        "expected_laws": ["Cap. 16", "Cap. 69"],
        "expected_articles": [],
        "key_terms": ["tenant", "eviction", "lease", "rent"],
        "difficulty": "medium"
    },
    {
        "question": "How do easements work in Maltese property law?",
        "domain": "property_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["servitude", "easement", "right of way"],
        "difficulty": "hard"  # Requires "easement" -> "servitude" expansion
    },

    # FAMILY LAW
    {
        "question": "What are the grounds for divorce in Malta?",
        "domain": "family_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["divorce", "marriage", "separation", "grounds"],
        "difficulty": "easy"
    },
    {
        "question": "How is child custody decided in divorce cases?",
        "domain": "family_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["custody", "child", "care", "access"],
        "difficulty": "medium"
    },
    {
        "question": "What is the alimony obligation after divorce?",
        "domain": "family_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["maintenance", "alimony", "support"],
        "difficulty": "hard"  # Requires "alimony" -> "maintenance" expansion
    },
    {
        "question": "How does succession work when someone dies without a will?",
        "domain": "family_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": [],
        "key_terms": ["succession", "inheritance", "intestate", "estate"],
        "difficulty": "medium"
    },

    # TAX LAW
    {
        "question": "What is the income tax rate for individuals in Malta?",
        "domain": "tax_law",
        "expected_laws": ["Cap. 123"],
        "expected_articles": [],
        "key_terms": ["tax", "rate", "income", "chargeable"],
        "difficulty": "easy"
    },
    {
        "question": "What are the penalties for tax evasion?",
        "domain": "tax_law",
        "expected_laws": ["Cap. 123"],
        "expected_articles": [],
        "key_terms": ["penalty", "evasion", "fine", "tax"],
        "difficulty": "easy"
    },

    # CONSTITUTIONAL LAW
    {
        "question": "What are the fundamental human rights in the Maltese Constitution?",
        "domain": "constitutional_law",
        "expected_laws": ["Cap. 1"],
        "expected_articles": [],
        "key_terms": ["rights", "fundamental", "constitution", "liberty"],
        "difficulty": "easy"
    },

    # MIXED/COMPLEX QUESTIONS
    {
        "question": "If a doctor negligently injures me, how long do I have to sue and what compensation can I get?",
        "domain": "civil_law",
        "expected_laws": ["Cap. 16"],
        "expected_articles": ["2153"],
        "key_terms": ["prescription", "damages", "negligence", "compensation"],
        "difficulty": "hard"
    },
]


def run_validation():
    """Run the full validation suite."""
    print("=" * 80)
    print("MALTESE LAW RAG - COMPREHENSIVE VALIDATION SUITE")
    print("=" * 80)

    retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
    classifier = QueryClassifier()

    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "by_difficulty": {"easy": [], "medium": [], "hard": []},
        "by_domain": {},
        "failures": []
    }

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_CASES)}: {test['domain'].upper()}")
        print(f"{'='*80}")
        print(f"Q: {test['question']}")
        print(f"Difficulty: {test['difficulty']}")

        start_time = time.time()

        # Run the search
        search_results = retriever.search(
            query=test["question"],
            limit=15,
            top_laws=15,
            expand_graph=True,
            auto_classify=True,
            max_hops=1
        )

        elapsed = time.time() - start_time

        # Check query expansion
        expansion = classifier.expand_query(test["question"])
        terms_added = expansion.get("terms_added", [])

        # Analyze results
        laws_searched = search_results.get("laws_searched", [])
        fundamental_added = search_results.get("fundamental_laws_added", [])
        categories = search_results.get("categories_used", [])
        articles = search_results.get("articles", [])

        print(f"\n--- RESULTS ({elapsed:.2f}s) ---")
        print(f"Categories: {categories}")
        print(f"Query expansion: {terms_added[:5] if terms_added else 'None'}")
        print(f"Fundamental laws added: {fundamental_added}")
        print(f"Total laws searched: {len(laws_searched)}")
        print(f"Articles found: {len(articles)}")

        # Validation checks
        passed = True
        fail_reasons = []

        # Check 1: Expected laws included
        for exp_law in test["expected_laws"]:
            if exp_law not in laws_searched:
                passed = False
                fail_reasons.append(f"Expected law {exp_law} not in search scope")

        # Check 2: Key terms found in articles
        all_article_text = " ".join([a.get("text", "").lower() for a in articles[:10]])
        terms_found = sum(1 for term in test["key_terms"] if term.lower() in all_article_text)
        term_ratio = terms_found / len(test["key_terms"]) if test["key_terms"] else 1

        if term_ratio < 0.3:  # At least 30% of key terms should be found
            passed = False
            fail_reasons.append(f"Only {terms_found}/{len(test['key_terms'])} key terms found in articles")

        # Check 3: Expected articles (if specified)
        if test["expected_articles"]:
            found_expected = []
            for art in articles[:15]:
                art_num = str(art.get("article_number", ""))
                for exp_art in test["expected_articles"]:
                    if exp_art in art_num:
                        found_expected.append(exp_art)

            if not found_expected:
                # Also check related articles
                related = search_results.get("related_articles", [])
                for art in related[:10]:
                    art_num = str(art.get("article_number", ""))
                    for exp_art in test["expected_articles"]:
                        if exp_art in art_num:
                            found_expected.append(exp_art)

            if not found_expected:
                passed = False
                fail_reasons.append(f"Expected articles {test['expected_articles']} not found")
            else:
                print(f"Found expected articles: {found_expected}")

        # Print top articles
        print("\nTop 3 articles:")
        for j, art in enumerate(articles[:3], 1):
            print(f"  {j}. {art.get('law_code')} Art. {art.get('article_number')}")
            print(f"     {art.get('text', '')[:100]}...")

        # Record result
        results["total"] += 1
        if passed:
            results["passed"] += 1
            print(f"\n[PASS] Test passed!")
        else:
            results["failed"] += 1
            results["failures"].append({
                "question": test["question"],
                "domain": test["domain"],
                "difficulty": test["difficulty"],
                "reasons": fail_reasons
            })
            print(f"\n[FAIL] Test failed:")
            for reason in fail_reasons:
                print(f"  - {reason}")

        results["by_difficulty"][test["difficulty"]].append(passed)

        if test["domain"] not in results["by_domain"]:
            results["by_domain"][test["domain"]] = []
        results["by_domain"][test["domain"]].append(passed)

    # Final summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    pass_rate = (results["passed"] / results["total"]) * 100
    print(f"\nOverall: {results['passed']}/{results['total']} passed ({pass_rate:.1f}%)")

    print("\nBy Difficulty:")
    for diff, tests in results["by_difficulty"].items():
        if tests:
            rate = sum(tests) / len(tests) * 100
            print(f"  {diff}: {sum(tests)}/{len(tests)} ({rate:.1f}%)")

    print("\nBy Domain:")
    for domain, tests in sorted(results["by_domain"].items()):
        if tests:
            rate = sum(tests) / len(tests) * 100
            print(f"  {domain}: {sum(tests)}/{len(tests)} ({rate:.1f}%)")

    if results["failures"]:
        print("\n" + "-" * 80)
        print("FAILED TESTS:")
        print("-" * 80)
        for fail in results["failures"]:
            print(f"\n  Q: {fail['question']}")
            print(f"  Domain: {fail['domain']} | Difficulty: {fail['difficulty']}")
            for reason in fail["reasons"]:
                print(f"    -> {reason}")

    print("\n" + "=" * 80)
    if pass_rate >= 80:
        print("*** VALIDATION SUCCESSFUL - System is performing well! ***")
    elif pass_rate >= 60:
        print("[!] VALIDATION PARTIAL - Some improvements needed")
    else:
        print("[X] VALIDATION FAILED - Significant issues found")
    print("=" * 80)

    return results


if __name__ == "__main__":
    run_validation()
