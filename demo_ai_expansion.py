"""
Simple Demo: AI Query Expansion - Keyword Fanning Feature
Shows how one simple question becomes 40+ legal terms
"""

from ai_query_expander import AIQueryExpander
import json

def demo_expansion():
    print("=" * 80)
    print("AI KEYWORD FANNING DEMONSTRATION")
    print("=" * 80)
    print("\nThis shows how AI 'fans out' a simple query into comprehensive legal terms\n")

    # Initialize the expander
    print("Initializing AI Query Expander (Claude 3.5 Sonnet)...")
    expander = AIQueryExpander()
    print("[OK] Ready!\n")

    # Example query
    query = "What are the payment procedures for property transfer tax?"

    print("-" * 80)
    print(f"USER QUERY:")
    print(f'"{query}"')
    print("-" * 80)
    print("\n[PROCESSING] Sending to Claude AI to generate Malta-specific legal terms...\n")

    # Get expansion
    expansion = expander.expand_query(query)

    # Display categorized results
    print("[SUCCESS] AI GENERATED TERMS (Categorized):")
    print("=" * 80)

    if expansion.get('official_terms'):
        print("\n[1] OFFICIAL MALTESE LEGAL TERMS:")
        for i, term in enumerate(expansion['official_terms'], 1):
            print(f"   {i}. {term}")

    if expansion.get('synonyms'):
        print("\n[2] SYNONYMS & ALTERNATIVE PHRASES:")
        for i, term in enumerate(expansion['synonyms'], 1):
            print(f"   {i}. {term}")

    if expansion.get('related_concepts'):
        print("\n[3] RELATED LEGAL CONCEPTS:")
        for i, term in enumerate(expansion['related_concepts'], 1):
            print(f"   {i}. {term}")

    if expansion.get('document_codes'):
        print("\n[4] RELEVANT LEGISLATION CODES:")
        for i, code in enumerate(expansion['document_codes'], 1):
            print(f"   {i}. {code}")

    if expansion.get('authorities'):
        print("\n[5] LEGAL AUTHORITIES/ENTITIES:")
        for i, auth in enumerate(expansion['authorities'], 1):
            print(f"   {i}. {auth}")

    if expansion.get('procedural_terms'):
        print("\n[6] PROCEDURAL TERMS:")
        for i, term in enumerate(expansion['procedural_terms'], 1):
            print(f"   {i}. {term}")

    # Count total terms
    total_terms = sum(len(v) for v in expansion.values() if isinstance(v, list))

    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"   Original query: {len(query.split())} words")
    print(f"   AI generated: {total_terms} additional terms")
    print(f"   Total expansion: {len(query.split()) + total_terms} search terms")
    print("=" * 80)

    # Show the final enhanced query
    enhanced_query = expander.generate_enhanced_query(query)
    print(f"\nFINAL ENHANCED QUERY STRING (sent to vector search):")
    print("-" * 80)
    print(enhanced_query[:400] + "...")
    print("-" * 80)
    print(f"   Length: {len(enhanced_query)} characters")
    print(f"   Words: ~{len(enhanced_query.split())}")

    print("\n" + "=" * 80)
    print("HOW THIS HELPS:")
    print("=" * 80)
    print("""
[+] Vector search now matches ANY of these 40+ terms
[+] Finds relevant articles even with different wording
[+] Works across ALL legal domains (tax, corporate, notarial, etc.)
[+] No hardcoding needed - AI adapts to any query
[+] Malta-specific terminology automatically generated
    """)

    # Show JSON for technical users
    print("\n" + "=" * 80)
    print("TECHNICAL: Raw JSON Response from AI")
    print("=" * 80)
    print(json.dumps(expansion, indent=2))

if __name__ == "__main__":
    try:
        demo_expansion()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nMake sure you have:")
        print("1. Set OPENROUTER_API_KEY in your .env file")
        print("2. Installed required packages: pip install openai python-dotenv")
