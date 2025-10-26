"""
Analyze actual content from legal documents to generate authentic questions
"""

import json
import random

# Load chunks
with open('processed_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

# Group by document
docs = {}
for chunk in chunks:
    doc = chunk['metadata']['document']
    if doc not in docs:
        docs[doc] = []
    docs[doc].append(chunk)

print("=" * 80)
print("CONTENT ANALYSIS FOR AUTHENTIC QUESTION GENERATION")
print("=" * 80)

# Key documents to analyze
key_docs = [
    "Duty on Documents and Transfers Act (Cap. 364)",
    "Tax on Property Transfers Rules (S.L. 123.92)",
    "First Time Buyers & Gozo Exemptions (S.L. 364.12)",
    "Companies Act (Cap. 386)",
    "Civil Code (Cap. 16)",
    "Notarial Profession and Notarial Archives Act (Cap. 55)",
    "Income Tax Act (Cap. 123)",
    "Prevention of Money Laundering Act (Cap. 373)",
    "Land Registration Act (Cap. 296)",
    "Private Residential Leases Act (Cap. 604)",
    "Cohabitation Act (Cap. 614)",
    "Real Estate Agents, Property Brokers and Property Consultants Act (Cap. 615)"
]

for doc_name in key_docs:
    if doc_name in docs:
        print(f"\n{'=' * 80}")
        print(f"{doc_name}")
        print('=' * 80)

        # Get sample articles
        sample = docs[doc_name][:5]

        for chunk in sample:
            article = chunk['metadata'].get('article', 'N/A')
            content = chunk['content'][:500]
            print(f"\nArticle {article}:")
            print(content)
            print("...")

        print(f"\nTotal articles in {doc_name}: {len(docs[doc_name])}")
