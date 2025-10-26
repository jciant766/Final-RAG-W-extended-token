"""
Integration guide: Replace hardcoded mappings with AI-powered expansion

This shows how to integrate AIQueryExpander into search_engine.py
"""

# OPTION 1: Replace existing _enhance_query method
# ================================================

def _enhance_query_with_ai(self, query: str, analysis: Dict) -> str:
    """
    AI-powered query enhancement
    Uses Claude to generate Maltese legal terminology
    """
    from ai_query_expander import AIQueryExpander
    
    # Initialize AI expander (cache this in __init__)
    if not hasattr(self, 'ai_expander'):
        try:
            self.ai_expander = AIQueryExpander()
        except Exception as e:
            self.debug.log("warning", f"AI expander failed to initialize: {e}")
            self.ai_expander = None
    
    expanded_parts = [query]
    
    # Use AI to expand query
    if self.ai_expander:
        try:
            expansion = self.ai_expander.expand_query(query)
            
            # Add official terms
            if expansion.get('official_terms'):
                expanded_parts.extend(expansion['official_terms'])
            
            # Add synonyms
            if expansion.get('synonyms'):
                expanded_parts.extend(expansion['synonyms'])
            
            # Add document codes
            if expansion.get('document_codes'):
                expanded_parts.extend(expansion['document_codes'])
            
            # Add authorities
            if expansion.get('authorities'):
                expanded_parts.extend(expansion['authorities'])
            
            # Add procedural terms
            if expansion.get('procedural_terms'):
                expanded_parts.extend(expansion['procedural_terms'])
            
            self.debug.log("info", f"AI expanded query to {len(expanded_parts)} terms")
            
        except Exception as e:
            self.debug.log("error", f"AI query expansion failed: {e}")
            # Fallback to basic enhancement
            pass
    
    # Fallback: Add basic intent enhancements if AI fails
    intent = analysis.get('intent')
    if intent and not self.ai_expander:
        basic_enhancements = {
            'procedural': 'procedure process steps filing submission',
            'penalty': 'penalty fine punishment offence',
            'requirement': 'requirement duty obligation must',
        }
        if intent in basic_enhancements:
            expanded_parts.append(basic_enhancements[intent])
    
    return " ".join(expanded_parts)


# OPTION 2: Hybrid approach (AI + hardcoded fallback)
# ===================================================

def _enhance_query_hybrid(self, query: str, analysis: Dict) -> str:
    """
    Hybrid: Try AI expansion first, fall back to hardcoded if AI fails
    Best of both worlds: flexibility + reliability
    """
    from ai_query_expander import AIQueryExpander
    
    expanded_parts = [query]
    ai_success = False
    
    # Try AI expansion first
    if not hasattr(self, 'ai_expander'):
        try:
            self.ai_expander = AIQueryExpander()
        except:
            self.ai_expander = None
    
    if self.ai_expander:
        try:
            expansion = self.ai_expander.expand_query(query)
            
            # Add all AI-generated terms
            for category in ['official_terms', 'synonyms', 'document_codes', 
                           'authorities', 'procedural_terms', 'related_concepts']:
                terms = expansion.get(category, [])
                if terms:
                    expanded_parts.extend(terms)
                    ai_success = True
            
            if ai_success:
                self.debug.log("info", f"AI expansion: {len(expanded_parts)} terms")
                return " ".join(expanded_parts)
        except Exception as e:
            self.debug.log("warning", f"AI expansion failed, using fallback: {e}")
    
    # Fallback to hardcoded mappings (your current implementation)
    query_lower = query.lower()
    
    # Tax queries
    if any(term in query_lower for term in ['property transfer tax', 'stamp duty', 'duty']):
        expanded_parts.extend(['stamp duty', 'duty on documents', 'transfer duty'])
    
    if 'payment' in query_lower:
        expanded_parts.extend(['remittance', 'submission', 'Commissioner'])
    
    # Add intent-based enhancements
    intent = analysis.get('intent')
    if intent == 'procedural':
        expanded_parts.append('procedure process steps filing submission')
    elif intent == 'penalty':
        expanded_parts.append('penalty fine punishment offence')
    
    return " ".join(expanded_parts)


# OPTION 3: Cached AI expansion (fast + comprehensive)
# ====================================================

class CachedAIExpander:
    """
    Cache AI-generated expansions for common queries
    First query: ~2 seconds (AI call)
    Subsequent: <1ms (cached)
    """
    def __init__(self):
        self.cache = {}
        self.ai_expander = None
        
        try:
            from ai_query_expander import AIQueryExpander
            self.ai_expander = AIQueryExpander()
        except:
            pass
    
    def expand_query(self, query: str) -> str:
        """Expand with caching"""
        # Check cache first
        if query in self.cache:
            return self.cache[query]
        
        # Generate expansion
        if self.ai_expander:
            try:
                enhanced = self.ai_expander.generate_enhanced_query(query)
                self.cache[query] = enhanced
                return enhanced
            except:
                pass
        
        # Fallback
        return query


# USAGE IN SEARCH_ENGINE.PY
# =========================

"""
In SearchEngine.__init__():

    def __init__(self, vector_store, enable_ai_overview=False):
        self.vector_store = vector_store
        self.debug = DebugLogger("search_engine")
        
        # Initialize AI query expander
        try:
            from ai_query_expander import AIQueryExpander
            self.ai_expander = AIQueryExpander()
            self.debug.log("info", "AI query expander initialized")
        except Exception as e:
            self.debug.log("warning", f"AI expander unavailable: {e}")
            self.ai_expander = None
        
        # ... rest of init


In SearchEngine._enhance_query():

    def _enhance_query(self, query: str, analysis: Dict) -> str:
        # Try AI expansion
        if self.ai_expander:
            try:
                return self.ai_expander.generate_enhanced_query(query)
            except Exception as e:
                self.debug.log("warning", f"AI expansion failed: {e}")
        
        # Fallback to hardcoded (current implementation)
        return self._enhance_query_fallback(query, analysis)
"""


# PERFORMANCE COMPARISON
# ======================

def compare_approaches():
    """
    Compare hardcoded vs AI-powered expansion
    """
    
    test_query = "What are the payment procedures for property transfer tax?"
    
    print("=" * 80)
    print("HARDCODED vs AI EXPANSION COMPARISON")
    print("=" * 80)
    
    # Hardcoded approach
    print("\n1. HARDCODED EXPANSION (Current):")
    print("-" * 80)
    hardcoded = [
        test_query,
        "procedure process steps filing submission remittance delivery",
        "stamp duty duty on documents duty on transfers transfer duty",
        "Commissioner Revenue",
        "Duty on Documents and Transfers Act Cap. 364"
    ]
    print(" ".join(hardcoded))
    print(f"\nTerms added: ~20-30")
    print(f"Coverage: Tax queries only")
    print(f"Maintenance: Requires manual updates")
    
    # AI approach
    print("\n2. AI-POWERED EXPANSION (Proposed):")
    print("-" * 80)
    try:
        from ai_query_expander import AIQueryExpander
        expander = AIQueryExpander()
        expansion = expander.expand_query(test_query)
        
        print("Official Terms:")
        print(f"  {expansion.get('official_terms', [])}")
        print("\nSynonyms:")
        print(f"  {expansion.get('synonyms', [])}")
        print("\nDocument Codes:")
        print(f"  {expansion.get('document_codes', [])}")
        print("\nAuthorities:")
        print(f"  {expansion.get('authorities', [])}")
        
        total_terms = sum(len(v) if isinstance(v, list) else 0 
                         for v in expansion.values())
        print(f"\nTerms added: {total_terms}")
        print(f"Coverage: ALL legal domains (tax, corporate, notarial, etc.)")
        print(f"Maintenance: Self-adapting, no manual updates needed")
        
    except Exception as e:
        print(f"AI expansion demo failed: {e}")
    
    print("\n" + "=" * 80)
    print("ADVANTAGES OF AI APPROACH:")
    print("=" * 80)
    print("✓ Works for ANY legal domain (not just tax)")
    print("✓ Adapts to new queries automatically")
    print("✓ No hardcoded mappings to maintain")
    print("✓ Understands legal context and nuance")
    print("✓ Generates Malta-specific terminology")
    print("✓ Can be cached for performance")
    print("✓ More comprehensive coverage")
    
    print("\n" + "=" * 80)
    print("TRADE-OFFS:")
    print("=" * 80)
    print("⚠ Adds ~1-2 seconds latency (first time only if cached)")
    print("⚠ Requires API calls (costs ~$0.001 per query)")
    print("⚠ Needs fallback for API failures")
    print("✓ But: Much more maintainable and comprehensive!")


if __name__ == "__main__":
    compare_approaches()


