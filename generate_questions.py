#!/usr/bin/env python3
import json
import random
from collections import defaultdict

def extract_questions_from_chunks():
    """Generate sample questions based on actual document content"""
    
    with open('processed_chunks.json', 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # Group by document type
    by_document = defaultdict(list)
    for chunk in chunks:
        doc = chunk['metadata'].get('document', 'Unknown')
        by_document[doc].append(chunk)
    
    questions = []
    
    # Companies Act questions
    companies_act_chunks = by_document.get('Companies Act (Cap. 386)', [])
    if companies_act_chunks:
        questions.extend([
            "What are the requirements for company registration?",
            "What are the penalties for late filing of annual accounts?",
            "What is the definition of a director under the Companies Act?",
            "What are the requirements for a company secretary?",
            "What constitutes a public company versus a private company?",
            "What are the obligations for maintaining accounting records?",
            "What is the procedure for company dissolution?",
            "What are the requirements for prospectus approval?",
            "What is the definition of a beneficial owner?",
            "What are the requirements for share capital?",
            "What penalties apply for non-compliance with audit requirements?",
            "What is the definition of an associated undertaking?",
            "What are the requirements for electronic communications?",
            "What constitutes a regulated market?",
            "What are the requirements for overseas companies?"
        ])
    
    # Subsidiary Legislation questions
    for doc_name, chunks in by_document.items():
        if 'S.L.' in doc_name:
            questions.extend([
                f"What are the requirements under {doc_name}?",
                f"What fees are applicable under {doc_name}?",
                f"What are the penalties for non-compliance with {doc_name}?",
                f"What procedures are specified in {doc_name}?",
                f"What are the registration requirements in {doc_name}?"
            ])
    
    # General legal questions based on content patterns
    questions.extend([
        "What are the legal requirements for commercial partnerships?",
        "What are the penalties for fraud in commercial transactions?",
        "What are the requirements for financial reporting?",
        "What constitutes a legal entity under Maltese law?",
        "What are the requirements for corporate governance?",
        "What are the obligations for data protection compliance?",
        "What are the requirements for cross-border transactions?",
        "What are the penalties for money laundering violations?",
        "What are the requirements for securities trading?",
        "What are the obligations for investor protection?"
    ])
    
    return questions

def main():
    print("=== Sample Questions for RAG Testing ===\n")
    
    questions = extract_questions_from_chunks()
    
    # Show questions by category
    print("📋 COMPANIES ACT QUESTIONS:")
    companies_questions = [q for q in questions if 'Companies Act' in q or 'company' in q.lower()]
    for i, q in enumerate(companies_questions[:10], 1):
        print(f"{i:2d}. {q}")
    
    print("\n📋 SUBSIDIARY LEGISLATION QUESTIONS:")
    sl_questions = [q for q in questions if 'S.L.' in q]
    for i, q in enumerate(sl_questions[:8], 1):
        print(f"{i:2d}. {q}")
    
    print("\n📋 GENERAL LEGAL QUESTIONS:")
    general_questions = [q for q in questions if not any(x in q for x in ['Companies Act', 'S.L.'])]
    for i, q in enumerate(general_questions[:10], 1):
        print(f"{i:2d}. {q}")
    
    print(f"\n✅ Total questions generated: {len(questions)}")
    print("\n💡 Try these questions in your Streamlit app at http://localhost:8501")

if __name__ == "__main__":
    main()

