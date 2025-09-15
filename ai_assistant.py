import os
import json
from typing import List, Dict, Any
import openai
from debug_logger import DebugLogger
from dotenv import load_dotenv

class AIAssistant:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2):
        self.debug = DebugLogger("ai_assistant")
        self.model = model
        self.temperature = temperature

        # Load environment variables if not already loaded (for local testing)
        load_dotenv()
        if os.path.exists('env'):
            load_dotenv('env', override=True)

        # Try to get API key from environment or Streamlit secrets
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENAI_API_KEY")
            except:
                pass
        
        if not api_key:
            self.debug.log("error", "OPENAI_API_KEY environment variable not set.")
            raise ValueError("OPENAI_API_KEY environment variable not set.")

        openai.api_key = api_key
        self.debug.log("info", f"AI Assistant initialized with model: {self.model}")

    def generate_overview(self, query: str, retrieved_articles: List[Dict], query_analysis: Dict = None) -> Dict:
        """
        Generate an AI overview based on retrieved articles
        """
        if not retrieved_articles:
            return {"overview": "No relevant articles found to generate an AI overview.", "citations": [], "confidence": 0}

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
        You are a legal research assistant specializing in Malta Commercial Code and Companies Act.
        Your task is to provide a concise, accurate, and non-hallucinatory overview
        of the legal topic related to the user's query, based *only* on the provided articles.
        If the provided articles are insufficient or do not address the query, say exactly:
        "Insufficient information in the corpus to answer this question."

        User Query: "{query}"
        User Intent: {intent or 'general information'}

        Retrieved Articles:
        {context}

        Instructions:
        1. Focus your response on the user's specific intent: {intent_instructions}
        2. Summarize the key legal points relevant to the query.
        3. Do NOT include any information not explicitly present in the provided articles.
        4. If the articles do not contain enough information to answer the query comprehensively, state that.
        5. Clearly cite the specific articles, their source law (document label), and page numbers from the "Retrieved Articles" section for each point made.
        6. Ensure the summary is easy to understand for a legal professional.
        7. Do not use phrases like "Based on the provided articles..." or "The articles state...". Just present the information directly.
        8. Format citations inline as "[Document] {{Art./Reg.}} X (Page Y)". Use the document label and citation provided in the context headers above.

        RESPONSE FORMAT:
        Provide your response as a clear, well-structured summary with proper citations focused on the user's intent."""

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a legal research assistant. Provide accurate, cited summaries based only on the provided legal text. Do not use external knowledge. If the context is insufficient, respond with: 'Insufficient information in the corpus to answer this question.'"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=500
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
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0,
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

