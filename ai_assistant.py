import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from debug_logger import DebugLogger
from dotenv import load_dotenv

class AIAssistant:
    def __init__(self, model: str = "anthropic/claude-4.5-sonnet", temperature: float = 0.1):
        self.debug = DebugLogger("ai_assistant")
        self.model = model
        self.temperature = temperature

        # Load environment variables if not already loaded (for local testing)
        load_dotenv()
        if os.path.exists('env'):
            load_dotenv('env', override=True)

        # Try to get OpenRouter API key from environment or Streamlit secrets
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENROUTER_API_KEY")
            except:
                pass
        
        if not api_key:
            self.debug.log("error", "OPENROUTER_API_KEY environment variable not set.")
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")

        # Use OpenRouter with base URL
        self.openai_client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.debug.log("info", f"AI Assistant initialized with OpenRouter model: {self.model} (1M+ context)")

    def generate_overview(self, query: str, retrieved_articles: List[Dict], query_analysis: Dict = None) -> Dict:
        """
        Generate an AI overview based on retrieved articles
        """
        if not retrieved_articles:
            return {"overview": "No relevant articles found to generate an AI overview.", "citations": [], "confidence": 0}

        # Extract unique documents with their overviews for context
        document_contexts = {}
        for a in retrieved_articles:
            md = a.get('metadata', {})
            doc_name = md.get('document', 'Unknown Document')
            if doc_name not in document_contexts:
                doc_overview = md.get('doc_overview', f"{doc_name}: Legal document.")
                document_contexts[doc_name] = doc_overview
        
        # Build document context section
        doc_context_text = "DOCUMENTS IN RETRIEVED RESULTS:\n"
        for i, (doc_name, overview) in enumerate(document_contexts.items(), 1):
            doc_context_text += f"{i}. {doc_name}\n   → {overview}\n"
        
        # Build rich context: include document label and citation for grounding
        context_lines = []
        for a in retrieved_articles:
            md = a.get('metadata', {})
            document = md.get('document', 'Unknown Document')
            citation = md.get('citation', f"Article {md.get('article', '?')}")
            page = md.get('page')
            # Always show page when it is a valid number
            page_num = None
            try:
                page_num = int(page)
            except Exception:
                page_num = None
            if page_num and page_num >= 1:
                header = f"[{document}] {citation} (Page {page_num})"
            else:
                header = f"[{document}] {citation}"
            context_lines.append(f"{header}:\n{a.get('content','')}")
        context = "\n\n".join(context_lines)

        # Extract unique citations for the overview
        citations = []
        seen = set()
        for article in retrieved_articles:
            md = article.get('metadata', {})
            key = (md.get('document'), md.get('article'), md.get('page'))
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                'document': md.get('document'),
                'citation': md.get('citation'),
                'article': md.get('article'),
                'page': md.get('page')
            })

        # Build intent-aware prompt based on user's detected intent
        intent = query_analysis.get('intent') if query_analysis else None
        intent_instructions = self._get_intent_instructions(intent)
        
        prompt = f"""
        You are an expert legal research assistant specializing in Maltese law.
        
        RETRIEVAL STRATEGY: You have been provided with {len(retrieved_articles)} articles using a broad retrieval approach. 
        Your role is to FILTER and SYNTHESIZE only the most relevant information for the user's specific query.
        
        {doc_context_text}
        
        User Query: "{query}"
        User Intent: {intent or 'general information'}

        Retrieved Articles ({len(retrieved_articles)} articles - some may be less relevant):
        {context}

        YOUR TASK:
        1. **FILTER**: From the {len(retrieved_articles)} articles, identify which ones DIRECTLY answer the query
        2. **PRIORITIZE**: Focus on the most relevant provisions first
        3. **SYNTHESIZE**: Combine related information from multiple sources
        4. **CITE ACCURATELY**: Reference specific articles, documents, and page numbers
        5. **CROSS-REFERENCE**: Note complementary or conflicting provisions across different laws
        
        INSTRUCTIONS:
        - Focus on user's intent: {intent_instructions}
        - IGNORE articles that are tangentially related or off-topic
        - Provide a comprehensive analysis of the RELEVANT legal points
        - Do NOT include information not explicitly present in the provided articles
        - Present information professionally without phrases like "Based on the articles..."
        - Format citations inline as "[Document] Art./Reg. X (Page Y)"
        - Use headings for complex topics with multiple aspects
        - If none of the articles adequately address the query, state this clearly
        
        QUALITY OVER QUANTITY: Better to provide a focused, accurate answer from 5-10 highly relevant articles 
        than to reference all {len(retrieved_articles)} articles indiscriminately.

        RESPONSE FORMAT:
        Provide a comprehensive, well-structured legal analysis with proper citations. Start with the most directly relevant provisions."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert legal research assistant for Maltese law with advanced filtering capabilities. You receive broad retrieval results and must identify the most relevant provisions. Provide comprehensive, accurately cited analyses based only on the provided legal text. Filter out less relevant results. Cross-reference related provisions. Do not use external knowledge. If insufficient relevant context exists, state this clearly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=4000  # Increased for comprehensive legal analysis with 1M+ context window
            )

            overview_text = response.choices[0].message.content.strip()

            # Calculate confidence based on article relevance scores
            avg_relevance = sum(article['score'] for article in retrieved_articles[:3]) / min(3, len(retrieved_articles))
            confidence = min(0.95, max(0.1, avg_relevance))

            result = {
                'overview': overview_text,
                'citations': citations,
                'confidence': confidence,
                'model_used': self.model,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'articles_analyzed': len(retrieved_articles)
            }

            self.debug.log("info", f"AI overview generated successfully. Confidence: {confidence:.2f}")
            return result

        except Exception as e:
            self.debug.log("error", f"Error calling OpenAI API: {e}")
            return {"overview": f"Error generating AI overview: {e}", "citations": [], "confidence": 0}

    def _get_intent_instructions(self, intent: str) -> str:
        """Get specific instructions based on user intent"""
        intent_map = {
            'definition': 'Provide clear definitions and meanings. Focus on explaining what terms mean and their legal significance.',
            'procedural': 'Focus on step-by-step procedures, processes, and how-to information. Explain the required steps and sequence.',
            'penalty': 'Focus on penalties, fines, punishments, and consequences. Explain what happens when rules are violated.',
            'requirement': 'Focus on requirements, duties, obligations, and what must be done. Explain mandatory actions and conditions.',
            'temporal': 'Focus on timing, deadlines, periods, and when things must happen. Explain time-related requirements.'
        }
        return intent_map.get(intent, 'Provide comprehensive information relevant to the user\'s query.')

