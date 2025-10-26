"""
Enhanced RAG System Test for Questions 10-25
Tests all new features: hybrid retrieval, query expansion, reranking, AI feedback loop
"""

import json
from search_engine import SearchEngine
from vector_store import VectorStore

def test_enhanced_rag():
    """Test enhanced RAG system with questions 10-25"""
    
    print("="*80)
    print("ENHANCED RAG SYSTEM TEST - Questions 10-25")
    print("="*80)
    print("\nFeatures enabled:")
    print("[+] Increased chunk retrieval (15 chunks, expandable to 25)")
    print("[+] Document overviews in metadata")
    print("[+] Hybrid retrieval (Semantic + BM25 keyword search)")
    print("[+] Enhanced query expansion")
    print("[+] Post-retrieval cross-encoder reranking")
    print("[+] AI feedback loop for adaptive retrieval")
    print("\n" + "="*80 + "\n")
    
    # Initialize system
    print("Initializing vector store...")
    vector_store = VectorStore()
    
    print("Initializing search engine with AI overview...")
    search_engine = SearchEngine(vector_store, enable_ai_overview=True)
    
    # Test questions 10-25
    questions = [
        "What are the steps for holding an AGM?",
        "How does a company change its name?",
        "What is the procedure for increasing share capital?",
        "How is bankruptcy declared?",
        "What is the process for protesting a bill of exchange?",
        "How are commercial disputes resolved?",
        "What are the duties of company directors?",
        "What are the reporting obligations for directors?",
        "What conflicts of interest rules apply to directors?",
        "What records must a company maintain?",
        "What are the requirements for dividend distributions?",
        "What are the requirements for a company to give financial assistance?",
        "What are beneficial ownership register requirements?",
        "Show me Article 4 of the Commercial Code",
        "What does Article 136A of the Companies Act say?",
        "Find Article 123 about dividends"
    ]
    
    results_summary = []
    
    for i, question in enumerate(questions, start=10):
        print(f"\n{'='*80}")
        print(f"Q{i}: {question}")
        print(f"{'='*80}")
        
        try:
            # Perform enhanced search
            result = search_engine.search(question, max_results=15, include_ai_overview=True)
            
            # Extract key information
            query_analysis = result.get('query_analysis', {})
            search_results = result.get('results', [])
            ai_overview = result.get('ai_overview', {})
            
            print(f"\n[QUERY ANALYSIS]")
            print(f"   - Type: {query_analysis.get('type', 'general')}")
            print(f"   - Intent: {query_analysis.get('intent', 'N/A')}")
            print(f"   - Document hint: {query_analysis.get('doc_hint', 'N/A')}")
            
            print(f"\n[SEARCH RESULTS] {len(search_results)} chunks retrieved")
            if search_results:
                print(f"   Top 3 sources:")
                for idx, r in enumerate(search_results[:3], 1):
                    citation = r.get('citation', 'Unknown')
                    score = r.get('score', 0)
                    has_overview = 'doc_overview' in r.get('metadata', {})
                    cross_encoder = r.get('cross_encoder_applied', False)
                    print(f"   {idx}. {citation} (score: {score:.3f})")
                    print(f"      - Has overview: {has_overview}")
                    print(f"      - Cross-encoder applied: {cross_encoder}")
            
            if ai_overview:
                print(f"\n[AI OVERVIEW]")
                print(f"   - Confidence: {ai_overview.get('confidence', 'N/A')}")
                print(f"   - Model: {ai_overview.get('model_used', 'N/A')}")
                print(f"   - Articles analyzed: {ai_overview.get('articles_analyzed', 0)}")
                print(f"   - Adaptive retrieval: {ai_overview.get('adaptive_retrieval', False)}")
                if ai_overview.get('adaptive_retrieval'):
                    print(f"   - Expanded from {ai_overview.get('expanded_from')} to {ai_overview.get('expanded_to')} chunks")
                
                overview_text = ai_overview.get('overview', '')
                print(f"\n   Overview (first 300 chars):")
                print(f"   {overview_text[:300]}...")
                
                citations = ai_overview.get('citations', [])
                print(f"\n   Citations: {len(citations)}")
                for cit in citations[:3]:
                    print(f"   - {cit}")
            
            # Summary for JSON
            results_summary.append({
                "question_number": i,
                "question": question,
                "chunks_retrieved": len(search_results),
                "confidence": ai_overview.get('confidence') if ai_overview else None,
                "adaptive_retrieval_used": ai_overview.get('adaptive_retrieval', False) if ai_overview else False,
                "top_citation": search_results[0].get('citation') if search_results else None,
                "has_overview": bool(ai_overview)
            })
            
            print("\n[OK] Test completed for this question")
            
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                "question_number": i,
                "question": question,
                "error": str(e)
            })
    
    # Save results
    output_file = "enhanced_rag_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"TEST COMPLETE!")
    print(f"{'='*80}")
    print(f"\nResults saved to: {output_file}")
    
    # Print summary statistics
    successful_tests = [r for r in results_summary if 'error' not in r]
    failed_tests = [r for r in results_summary if 'error' in r]
    
    print(f"\n[SUMMARY STATISTICS]")
    print(f"   - Total questions: {len(questions)}")
    print(f"   - Successful: {len(successful_tests)}")
    print(f"   - Failed: {len(failed_tests)}")
    
    if successful_tests:
        avg_chunks = sum(r['chunks_retrieved'] for r in successful_tests) / len(successful_tests)
        avg_confidence = sum(r['confidence'] for r in successful_tests if r['confidence']) / len([r for r in successful_tests if r['confidence']])
        adaptive_count = sum(1 for r in successful_tests if r['adaptive_retrieval_used'])
        
        print(f"   - Average chunks retrieved: {avg_chunks:.1f}")
        print(f"   - Average confidence: {avg_confidence:.2f}")
        print(f"   - Adaptive retrieval triggered: {adaptive_count} times")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    test_enhanced_rag()

