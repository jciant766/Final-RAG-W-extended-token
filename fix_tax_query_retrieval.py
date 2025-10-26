"""
Fix for Tax Query Retrieval Failure
Adds tax-specific term mapping and query enhancement
"""

# This shows what needs to be added to search_engine.py

TAX_QUERY_ENHANCEMENTS = {
    # Core tax terminology synonyms
    'tax_terms': {
        'property transfer tax': ['stamp duty', 'duty on documents', 'transfer duty', 'duty on transfers', 
                                   'document duty', 'conveyance duty', 'registration duty'],
        'transfer tax': ['stamp duty', 'duty on documents', 'duty on transfers', 'document duty'],
        'stamp duty': ['duty on documents', 'transfer duty', 'property transfer tax', 'conveyance duty'],
        'duty': ['stamp duty', 'tax', 'charge', 'levy', 'impost'],
        
        # Payment-related terms
        'payment': ['remittance', 'submission', 'delivery', 'settlement', 'discharge'],
        'pay': ['remit', 'submit', 'deliver', 'settle', 'discharge'],
        'payment procedure': ['submission procedure', 'remittance procedure', 'payment process', 
                              'how to pay', 'delivery to Commissioner'],
        
        # Tax authority terms
        'tax authority': ['Commissioner', 'Commissioner for Revenue', 'Revenue Commissioner'],
        'submit to': ['deliver to', 'file with', 'remit to', 'give notice to'],
        
        # Specific tax document terms
        'property tax': ['property transfer tax', 'stamp duty', 'duty on immovable property', 
                         'real estate tax', 'conveyance tax'],
        'first time buyer': ['first-time buyer', 'first acquisition', 'prima casa', 'first property'],
        
        # Capital gains related
        'capital gains': ['capital gains tax', 'gains on transfer', 'transfer gains', 'property gains'],
        
        # Document-specific terms
        'deed': ['notarial deed', 'public deed', 'contract', 'instrument'],
        'transfer': ['conveyance', 'assignment', 'disposition', 'sale'],
        'registration': ['filing', 'recording', 'lodgment', 'submission'],
    },
    
    # Document hints for tax queries
    'document_hints': {
        'duty': 'cap_364',  # Duty on Documents and Transfers Act
        'stamp duty': 'cap_364',
        'transfer tax': ['cap_364', 'sl_123_92'],  # Cap 364 + S.L. 123.92
        'property transfer tax': ['cap_364', 'sl_123_92'],
        'first time buyer': 'sl_364_12',  # S.L. 364.12
        'first-time buyer': 'sl_364_12',
        'gozo property': 'sl_364_12',
        'capital gains': 'sl_123_27',  # S.L. 123.27
        'property gains': 'sl_123_27',
        'vacant property': ['sl_123_203', 'sl_364_19'],
        'uca': ['sl_123_203', 'sl_364_19'],
        'urban conservation': ['sl_123_203', 'sl_364_19'],
    }
}

# Pattern detection for tax queries
TAX_QUERY_PATTERNS = {
    'stamp_duty': r'\b(stamp\s+duty|duty\s+on\s+documents?|transfer\s+duty|property\s+transfer\s+tax)\b',
    'payment_procedure': r'\b(payment\s+procedure|how\s+to\s+pay|submission\s+procedure|when\s+to\s+pay|deadline)\b',
    'exemption': r'\b(exemption|relief|reduced\s+rate|first[\s-]time\s+buyer|gozo)\b',
    'calculation': r'\b(calculat|comput|assess|determin|rate|percentage)\b',
    'capital_gains': r'\b(capital\s+gains?|gains?\s+tax|property\s+gains?)\b',
}

def enhanced_query_for_tax(query: str) -> dict:
    """
    Detect if query is tax-related and return enhancements
    """
    import re
    
    query_lower = query.lower()
    
    # Detect tax query type
    tax_type = None
    if re.search(TAX_QUERY_PATTERNS['stamp_duty'], query_lower):
        tax_type = 'stamp_duty'
    elif re.search(TAX_QUERY_PATTERNS['capital_gains'], query_lower):
        tax_type = 'capital_gains'
    elif any(term in query_lower for term in ['first time', 'first-time', 'gozo']):
        tax_type = 'exemption'
    
    # Build enhancement package
    enhancements = {
        'is_tax_query': tax_type is not None,
        'tax_type': tax_type,
        'expansion_terms': [],
        'document_codes': []
    }
    
    if tax_type:
        # Add synonym expansions
        for original_term, synonyms in TAX_QUERY_ENHANCEMENTS['tax_terms'].items():
            if original_term in query_lower:
                enhancements['expansion_terms'].extend(synonyms)
        
        # Add document hints
        for hint_term, doc_codes in TAX_QUERY_ENHANCEMENTS['document_hints'].items():
            if hint_term in query_lower:
                if isinstance(doc_codes, list):
                    enhancements['document_codes'].extend(doc_codes)
                else:
                    enhancements['document_codes'].append(doc_codes)
    
    return enhancements


# Example usage
if __name__ == "__main__":
    # Test the problem query
    query = "What are the payment procedures for property transfer tax?"
    
    result = enhanced_query_for_tax(query)
    
    print(f"Query: {query}")
    print(f"\nIs Tax Query: {result['is_tax_query']}")
    print(f"Tax Type: {result['tax_type']}")
    print(f"\nExpansion Terms: {result['expansion_terms'][:10]}")  # First 10
    print(f"\nTarget Documents: {result['document_codes']}")
    
    # Expected output:
    # Expansion Terms: ['stamp duty', 'duty on documents', 'transfer duty', ...]
    # Target Documents: ['cap_364', 'sl_123_92']


