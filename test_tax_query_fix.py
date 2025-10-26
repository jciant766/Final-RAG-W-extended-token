"""
Test script to verify tax query retrieval fix
Run this to verify Cap. 364 and S.L. 123.92 are now being retrieved
"""

from search_engine import SearchEngine
from vector_store import VectorStore

def test_tax_queries():
    print("=" * 80)
    print("TESTING TAX QUERY RETRIEVAL FIX")
    print("=" * 80)
    
    # Initialize
    vector_store = VectorStore()
    search_engine = SearchEngine(vector_store, enable_ai_overview=True)
    
    # Test queries
    test_cases = [
        {
            'query': "What are the payment procedures for property transfer tax?",
            'expected_docs': ['cap_364', 'sl_123_92'],
            'description': "Original failing query"
        },
        {
            'query': "How do I pay stamp duty on property?",
            'expected_docs': ['cap_364', 'sl_364_06'],
            'description': "Stamp duty payment"
        },
        {
            'query': "What exemptions exist for first-time buyers?",
            'expected_docs': ['sl_364_12'],
            'description': "First-time buyer exemptions"
        },
        {
            'query': "How do I calculate capital gains on property sale?",
            'expected_docs': ['sl_123_27'],
            'description': "Capital gains calculation"
        },
        {
            'query': "What is the deadline for submitting duty on documents?",
            'expected_docs': ['cap_364', 'sl_123_92'],
            'description': "Duty submission deadline"
        }
    ]
    
    results_summary = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'-' * 80}")
        print(f"TEST {i}: {test['description']}")
        print(f"Query: {test['query']}")
        print(f"-" * 80)
        
        # Run search
        search_payload = search_engine.search(test['query'], max_results=30)
        results = search_payload.get('results', [])
        
        # Extract doc codes from top 10
        top_10_docs = [r['metadata']['doc_code'] for r in results[:10]]
        top_10_names = [r['metadata']['document'] for r in results[:10]]
        
        # Check if expected docs found
        found = []
        missing = []
        for expected in test['expected_docs']:
            if expected in top_10_docs:
                found.append(expected)
            else:
                missing.append(expected)
        
        # Print results
        print(f"\nTop 10 Documents Retrieved:")
        for idx, (doc_code, doc_name) in enumerate(zip(top_10_docs, top_10_names), 1):
            marker = "✓" if doc_code in test['expected_docs'] else " "
            print(f"  [{marker}] {idx}. {doc_code:20s} - {doc_name}")
        
        print(f"\nExpected Documents:")
        for doc in test['expected_docs']:
            status = "✓ FOUND" if doc in found else "✗ MISSING"
            position = top_10_docs.index(doc) + 1 if doc in top_10_docs else "N/A"
            print(f"  {status:10s} {doc:20s} (Position: {position})")
        
        # Check AI overview
        ai_overview = search_payload.get('ai_overview', {})
        citations = ai_overview.get('citations', [])
        cited_docs = set(c.get('document', '') for c in citations)
        
        print(f"\nAI Overview Citations: {len(citations)} total")
        expected_cited = any(
            any(expected in doc.lower() or expected.replace('_', '.') in doc.lower() 
                for expected in test['expected_docs'])
            for doc in cited_docs
        )
        print(f"  Expected docs cited: {'✓ YES' if expected_cited else '✗ NO'}")
        
        # Store summary
        success = len(missing) == 0
        results_summary.append({
            'test': test['description'],
            'success': success,
            'found': len(found),
            'expected': len(test['expected_docs'])
        })
        
        print(f"\nResult: {'✓ PASS' if success else '✗ FAIL'}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_tests = len(test_cases)
    passed = sum(1 for r in results_summary if r['success'])
    
    for i, result in enumerate(results_summary, 1):
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        print(f"{status} Test {i}: {result['test']:40s} ({result['found']}/{result['expected']} docs found)")
    
    print(f"\n{'-' * 80}")
    print(f"Overall: {passed}/{total_tests} tests passed ({passed/total_tests*100:.0f}%)")
    
    if passed == total_tests:
        print("\n🎉 SUCCESS! All tax queries now retrieve correct documents!")
    elif passed >= total_tests * 0.8:
        print("\n⚠️  MOSTLY WORKING - Some queries need tuning")
    else:
        print("\n❌ FIX NOT WORKING - Further debugging needed")
    
    print("=" * 80)
    
    return passed == total_tests


if __name__ == "__main__":
    try:
        success = test_tax_queries()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


