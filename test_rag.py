import json
from search_engine import SearchEngine
from vector_store import VectorStore

vector_store = VectorStore()
search_engine = SearchEngine(vector_store, enable_ai_overview=True)

questions = [
    "What is a trader?",
    "Define acts of trade",
    "What is commercial representation?",
    "What is a bill of exchange?",
    "What is a private limited liability company?",
    "Define share capital",
    "What is a company secretary and what are their duties?",
    "What is the meaning of \"shadow director\"?",
    "How do I register a new company in Malta?",
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
    "Find Article 123 about dividends",
    "What is in Article 477 of the Commercial Code?",
    "What are all the rules about cell companies?",
    "Tell me about protected cell companies",
    "What are the rules for incorporated cell companies?",
    "What regulations apply to investment services companies?",
    "Article 4",
    "Director duties",
    "Bankruptcy",
    "Share transfer",
    "Company formation",
    "What is the solvency test for distributions?",
    "What are the rules for issuing debentures?",
    "Can a company purchase its own shares?",
    "What are the requirements for audited accounts?",
    "What are the capital maintenance rules?",
    "What are the penalties for late filing of annual returns?",
    "What happens if a director breaches their duties?",
    "What are the consequences of trading while insolvent?",
    "What are the rules for foreign companies operating in Malta?",
    "What is a European company (SE)?",
    "What are the rules for single member companies?",
    "Article 9999 of the Commercial Code",
    "What is the legal definition of a unicorn company?",
    "Show me all articles about blockchain",
    "What does the law say about AI-generated contracts?"
]

results = []
for q in questions:
    result = search_engine.search(q)
    results.append({"question": q, "result": result})

with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("Results written to test_results.json")
