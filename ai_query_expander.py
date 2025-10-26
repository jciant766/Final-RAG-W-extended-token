"""
AI-Powered Query Expansion for Legal Searches
Uses Claude to generate Malta-specific legal terminology variants
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

class AIQueryExpander:
    def __init__(self):
        load_dotenv()
        if os.path.exists('env'):
            load_dotenv('env', override=True)
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENROUTER_API_KEY")
            except:
                pass
        
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = "anthropic/claude-3.5-sonnet"
    
    def expand_query(self, user_query: str) -> Dict[str, List[str]]:
        """
        Use AI to generate Maltese legal terminology variants
        
        Returns:
        {
            'synonyms': ['term1', 'term2', ...],
            'related_terms': ['related1', 'related2', ...],
            'document_types': ['Cap. 364', 'S.L. 123.92', ...],
            'legal_concepts': ['concept1', 'concept2', ...]
        }
        """
        
        prompt = f"""You are a Maltese legal terminology expert. A user searching Maltese legislation asked:

"{user_query}"

Generate search terms to help retrieve relevant Maltese legal documents. Consider:

1. **Official Maltese Legal Terms**: What exact phrases appear in Maltese legislation?
   - Example: "property transfer tax" → "duty on documents and transfers", "stamp duty"
   
2. **Synonyms**: Alternative ways to express the same concept
   - Example: "payment" → "remittance", "submission", "delivery"

3. **Related Legal Concepts**: Connected topics that might be relevant
   - Example: "tax exemptions" → "relief", "reduced rate", "first-time buyer"

4. **Likely Document References**: Which Malta legislation chapters (Cap.) or subsidiary legislation (S.L.) would cover this?
   - Example: tax queries → "Cap. 364", "S.L. 123.92"

5. **Legal Entities/Authorities**: Which authorities or roles are involved?
   - Example: "Commissioner for Revenue", "notary", "Registrar"

Respond in this exact JSON format:
{{
  "official_terms": ["term1", "term2"],
  "synonyms": ["synonym1", "synonym2"],
  "related_concepts": ["concept1", "concept2"],
  "document_codes": ["Cap. 364", "S.L. 123.92"],
  "authorities": ["authority1", "authority2"],
  "procedural_terms": ["procedure1", "procedure2"]
}}

Focus on Maltese legal terminology. Be specific to Malta's legal system."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in Maltese legal terminology and legislation. Provide only valid JSON responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for consistent terminology
                max_tokens=1000
            )
            
            # Parse JSON response
            import json
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            expansion = json.loads(result_text)
            
            return expansion
            
        except Exception as e:
            print(f"Query expansion failed: {e}")
            # Fallback to basic expansion
            return {
                'official_terms': [user_query],
                'synonyms': [],
                'related_concepts': [],
                'document_codes': [],
                'authorities': [],
                'procedural_terms': []
            }
    
    def generate_enhanced_query(self, user_query: str) -> str:
        """
        Generate complete enhanced query string for vector search
        """
        expansion = self.expand_query(user_query)
        
        # Combine all expansion terms
        all_terms = [user_query]
        
        for category, terms in expansion.items():
            if terms:
                all_terms.extend(terms)
        
        # Create enhanced query
        enhanced = " ".join(all_terms)
        
        return enhanced
    
    def get_expansion_report(self, user_query: str) -> str:
        """
        Get human-readable report of query expansion
        """
        expansion = self.expand_query(user_query)
        
        report = f"Original Query: {user_query}\n"
        report += "=" * 80 + "\n\n"
        
        report += "AI-Generated Expansion:\n\n"
        
        if expansion.get('official_terms'):
            report += "Official Maltese Terms:\n"
            for term in expansion['official_terms']:
                report += f"  - {term}\n"
            report += "\n"
        
        if expansion.get('synonyms'):
            report += "Synonyms:\n"
            for term in expansion['synonyms']:
                report += f"  - {term}\n"
            report += "\n"
        
        if expansion.get('document_codes'):
            report += "Relevant Legislation:\n"
            for doc in expansion['document_codes']:
                report += f"  - {doc}\n"
            report += "\n"
        
        if expansion.get('authorities'):
            report += "Legal Authorities:\n"
            for auth in expansion['authorities']:
                report += f"  - {auth}\n"
            report += "\n"
        
        if expansion.get('procedural_terms'):
            report += "Procedural Terms:\n"
            for term in expansion['procedural_terms']:
                report += f"  - {term}\n"
            report += "\n"
        
        return report


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("AI-POWERED QUERY EXPANSION TEST")
    print("=" * 80)
    
    expander = AIQueryExpander()
    
    # Test with the failing query
    test_queries = [
        "What are the payment procedures for property transfer tax?",
        "How do I calculate stamp duty?",
        "What exemptions exist for first-time buyers?",
        "How do notaries examine property title?",
        "What are the director's duties in a company?"
    ]
    
    for query in test_queries:
        print(f"\n{'-' * 80}")
        print(expander.get_expansion_report(query))
        print(f"\nEnhanced Query String:")
        enhanced = expander.generate_enhanced_query(query)
        print(f"{enhanced[:200]}...")  # First 200 chars
        print(f"(Total length: {len(enhanced)} chars)")


