import json
from search_engine import SearchEngine
from vector_store import VectorStore

vector_store = VectorStore()  # Assumes overviews in metadata
search_engine = SearchEngine(vector_store)

# Sample overviews (in real setup, add to chunk metadata during processing)
DOC_OVERVIEWS = {
    "companies_act": "Companies Act (Cap. 386): Governs company formation, governance, directors' duties, shares, and financial regulations in Malta.",
    "code_13": "Commercial Code (Cap. 13): Covers traders, acts of trade, bills of exchange, bankruptcy, and commercial disputes."
    # Add more as needed
}

questions_10_25 = [  # Your Q10-25
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

# Mock simulate_grep without real files (for demo)
def simulate_grep(query):
    # Hardcoded mock results for testing
    mock_content = """
Line about AGM from Companies Act.
Procedure for name change in Art. 80.
Bankruptcy declaration in Commercial Code Art. 481.
    """  # etc.
    results = [line for line in mock_content.splitlines() if query.lower() in line.lower()]
    return '\n'.join(results)

def enhanced_search(query):
    # Query Expansion: Generate variants
    expansions = [query, f"rules for {query}", f"requirements of {query}"]  # Simple; can use AI for better
    
    all_chunks = []
    for exp in expansions:
        # Semantic search
        sem_results = search_engine.vector_store.search(exp, n_results=10)
        all_chunks.extend(sem_results)
        
        # Keyword search (hybrid)
        kw_results = simulate_grep(exp)
        all_chunks.extend([{"content": line, "metadata": {}} for line in kw_results.splitlines() if line])
    
    # Rerank: Mock simple rerank (boost if keyword match)
    for chunk in all_chunks:
        chunk['rerank_score'] = chunk.get('score', 0) + (1 if query in chunk['content'] else 0)
    all_chunks = sorted(all_chunks, key=lambda x: x['rerank_score'], reverse=True)[:15]
    
    # Add overviews to chunks
    for chunk in all_chunks:
        doc = chunk['metadata'].get('doc_code')
        if doc in DOC_OVERVIEWS:
            chunk['metadata']['doc_overview'] = DOC_OVERVIEWS[doc]
    
    # AI Feedback Loop: If initial overview low-confidence, expand
    initial_overview = search_engine.ai_assistant.generate_overview(query, all_chunks[:10])  # Pseudo-call
    if initial_overview['confidence'] < 0.7:
        # Retrieve more (e.g., next 10)
        more_chunks = search_engine.vector_store.search(query, n_results=20)[10:]
        all_chunks.extend(more_chunks)
        return search_engine.ai_assistant.generate_overview(query, all_chunks)  # Rerun
    return initial_overview

results = []
for q in questions_10_25:
    result = enhanced_search(q)
    results.append({"question": q, "result": result})

with open("enhanced_results_10_25.json", "w") as f:
    json.dump(results, f, indent=2)

print("Enhanced results for Q10-25 written to enhanced_results_10_25.json")
