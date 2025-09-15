import re
from typing import List, Dict, Tuple
from debug_logger import DebugLogger

class SearchEngine:
    """Intelligent search with automatic query understanding"""
    
    def __init__(self, vector_store, enable_ai_overview=False):
        self.vector_store = vector_store
        self.debug = DebugLogger("search_engine")
        self.enable_ai_overview = enable_ai_overview
        
        # Initialize AI assistant if enabled
        if enable_ai_overview:
            try:
                from ai_assistant import AIAssistant
                self.ai_assistant = AIAssistant()
                self.debug.log("info", "AI Assistant initialized")
            except Exception as e:
                self.debug.log("error", f"Failed to initialize AI Assistant: {e}")
                self.enable_ai_overview = False
                self.ai_assistant = None
        else:
            self.ai_assistant = None
        
    def search(self, query: str, max_results: int = 5, include_ai_overview: bool = True) -> Dict:
        """Smart search with automatic detection and AI overview"""
        self.debug.log("info", f"Processing query: {query}")
        
        # Clean query
        query = query.strip()
        
        # Detect query type and intent
        query_analysis = self._analyze_query(query)
        self.debug.log("debug", f"Query analysis: {query_analysis}")
        
        # Execute appropriate search
        if query_analysis['type'] == 'article_lookup':
            results = self._article_search(query_analysis['article_num'], query_analysis.get('doc_hint'))
        else:
            # Semantic search with query enhancement
            enhanced_query = self._enhance_query(query, query_analysis)
            filters = None
            if query_analysis.get('doc_hint') in {'companies_act', 'code_13'}:
                filters = { 'doc_code': query_analysis['doc_hint'] }
            results = self.vector_store.search(enhanced_query, n_results=max_results, filters=filters)
            if results:
                results = self._rerank_results_by_intent(results, query_analysis)

        # Strict evidence gate: if top result is weak, return no results
        MIN_TOP_SCORE = 0.45
        if not results or results[0].get('score', 0.0) < MIN_TOP_SCORE:
            results = []
        
        # Log results
        self.debug.log("info", f"Found {len(results)} results")
        for r in results[:3]:  # Log top 3
            self.debug.log("debug", 
                f"  - {r['citation']}: {r['score']:.3f}")
        
        # Generate AI overview if enabled and not a direct article lookup
        ai_overview = None
        if (self.enable_ai_overview and 
            include_ai_overview and 
            query_analysis['type'] != 'article_lookup' and 
            results and 
            self.ai_assistant):
            try:
                ai_overview = self.ai_assistant.generate_overview(query, results, query_analysis)
                self.debug.log("info", "AI overview generated successfully")
            except Exception as e:
                self.debug.log("error", f"Failed to generate AI overview: {e}")
                ai_overview = None
        
        return {
            'query': query,
            'query_analysis': query_analysis,
            'results': results,
            'ai_overview': ai_overview
        }
    
    def _analyze_query(self, query: str) -> Dict:
        """Analyze query intent and type"""
        analysis = {
            'type': 'general',
            'intent': None,
            'keywords': [],
            'article_num': None,
            'doc_hint': None
        }
        
        query_lower = query.lower()
        
        # Check for article reference
        article_patterns = [
            r'\b(?:article|art\.?)\s*(\d+[A-Z]?)\b',
            r'\b(\d+[A-Z]?)\s*(?:of|from|in)\s*(?:the\s*)?(?:commercial\s*)?code\b',
            r'^(\d+[A-Z]?)$'  # Just a number
        ]
        
        for pattern in article_patterns:
            match = re.search(pattern, query_lower)
            if match:
                analysis['type'] = 'article_lookup'
                analysis['article_num'] = match.group(1).upper()
                break
        
        # Detect document hint (Companies Act vs Commercial Code vs Subsidiary Legislation)
        if any(term in query_lower for term in ['companies act', 'cap. 386', 'cap 386', 'companies']):
            analysis['doc_hint'] = 'companies_act'
        elif any(term in query_lower for term in ['commercial code', 'cap. 13', 'cap 13']):
            analysis['doc_hint'] = 'code_13'
        elif 's.l.' in query_lower or 'subsidiary legislation' in query_lower:
            # leave generic; vector layer carries precise code
            analysis['doc_hint'] = 'sl'
        
        if analysis['type'] == 'article_lookup' and analysis['doc_hint']:
            return analysis
        
        # Detect intent
        if any(word in query_lower for word in ['what is', 'define', 'meaning']):
            analysis['intent'] = 'definition'
        elif any(word in query_lower for word in ['how to', 'procedure', 'process']):
            analysis['intent'] = 'procedural'
        elif any(word in query_lower for word in ['penalty', 'fine', 'punishment']):
            analysis['intent'] = 'penalty'
        elif any(word in query_lower for word in ['requirement', 'duty', 'obligation']):
            analysis['intent'] = 'requirement'
        elif any(word in query_lower for word in ['when', 'time', 'deadline', 'period']):
            analysis['intent'] = 'temporal'
        
        # Extract key terms
        keywords = self._extract_keywords(query)
        analysis['keywords'] = keywords
        
        return analysis
    
    def _article_search(self, article_num: str, doc_hint: str = None) -> List[Dict]:
        """Direct article lookup"""
        # Try hinted doc first
        results = self.vector_store.get_article(article_num, doc_hint) if doc_hint else []
        
        # If no hint or not found, try common corpora in order
        if not results:
            for candidate_doc in (['companies_act', 'code_13'] if doc_hint is None else []):
                results = self.vector_store.get_article(article_num, candidate_doc)
                if results:
                    break
        
        if not results:
            # Fallback to semantic search
            query = f"Article {article_num} Malta Commercial Code or Companies Act"
            filters = { 'doc_code': doc_hint } if doc_hint in {'companies_act', 'code_13'} else None
            results = self.vector_store.search(query, n_results=5, filters=filters)
        
        return results
    
    def _enhance_query(self, query: str, analysis: Dict) -> str:
        """Enhance query based on intent and extracted keywords.
        This performs lightweight query expansion to guide vector search
        without altering the original semantics.
        """
        enhancements = {
            'definition': 'definition meaning interpret define term construed means',
            'procedural': 'procedure process steps how to application shall apply filing',
            'penalty': 'penalty fine punishment offence liable conviction contravention sanctions',
            'requirement': 'requirement duty obligation must shall required compliance',
            'temporal': 'time period deadline within days months not later than when'
        }

        expanded_parts = [query]

        intent = analysis.get('intent')
        if intent and intent in enhancements:
            expanded_parts.append(enhancements[intent])

        # Add extracted keywords to reinforce important terms
        keywords = analysis.get('keywords') or []
        if keywords:
            expanded_parts.append(" ".join(keywords))

        # Nudge towards the hinted corpus when present
        doc_hint = analysis.get('doc_hint')
        if doc_hint == 'companies_act':
            expanded_parts.append('Companies Act Cap. 386')
        elif doc_hint == 'code_13':
            expanded_parts.append('Commercial Code Cap. 13')

        return " ".join(expanded_parts)

    def _score_boost_by_intent(self, result: Dict, analysis: Dict) -> float:
        """Lightweight reranking: add small boosts when content matches intent cues."""
        content = (result.get('content') or '').lower()
        intent = analysis.get('intent')
        boost = 0.0
        if intent == 'definition' and ('means' in content or 'for the purposes of this' in content):
            boost += 0.05
        elif intent == 'procedural' and any(p in content for p in ['shall', 'procedure', 'steps', 'application']):
            boost += 0.05
        elif intent == 'penalty' and any(p in content for p in ['penalty', 'fine', 'liable', 'offence', 'contravention']):
            boost += 0.07
        elif intent == 'requirement' and any(p in content for p in ['must', 'shall', 'required', 'requirements']):
            boost += 0.04
        elif intent == 'temporal' and any(p in content for p in ['days', 'months', 'within', 'not later than']):
            boost += 0.04
        # Prefer exact numeric mention of "article N" inside the chunk
        import re as _re
        m = _re.search(r"\barticle\s+(\d+[a-z]?)\b", content)
        if m and analysis.get('article_num') and m.group(1).upper() == analysis['article_num'].upper():
            boost += 0.1
        return boost

    def _rerank_results_by_intent(self, results: List[Dict], analysis: Dict) -> List[Dict]:
        """Apply intent-based boosts and return sorted results."""
        rescored = []
        for r in results:
            boost = self._score_boost_by_intent(r, analysis)
            r2 = dict(r)
            r2['score'] = max(0.0, min(1.0, r.get('score', 0) + boost))
            rescored.append(r2)
        rescored.sort(key=lambda x: x['score'], reverse=True)
        return rescored
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords"""
        # Remove common words
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'what', 'who', 'where', 
            'when', 'how', 'can', 'do', 'does', 'in', 'of', 'to',
            'for', 'with', 'about', 'malta', 'code', 'commercial'
        }
        
        # Legal terms to preserve
        legal_terms = {
            'bankruptcy', 'bankrupt', 'trader', 'bill', 'exchange',
            'insurance', 'marine', 'broker', 'agent', 'fraud',
            'penalty', 'contract', 'obligation', 'debt'
        }
        
        words = query.lower().split()
        keywords = []
        
        for word in words:
            word = word.strip('.,?!')
            if word and (word not in stopwords or word in legal_terms):
                keywords.append(word)
        
        return keywords
