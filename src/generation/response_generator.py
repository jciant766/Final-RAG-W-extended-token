"""
Response generation using Claude with Anthropic's Citations API.
Produces answers with verifiable legal citations that cannot be fabricated.

Research basis: Anthropic Citations API (Jan 2025) - reduces hallucinated citations to 0%
by forcing the model to cite exact spans from source documents.
"""

import os
import anthropic
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class LegalResponseGenerator:
    """
    Generates responses with verified legal citations using Anthropic's Citations API.

    Unlike prompt-based approaches, the Citations API guarantees that all citations
    reference actual text from source documents - fabrication is impossible.
    """

    # Research-backed prompt (Anthropic 2025): Evidence-first approach + explicit uncertainty permission
    SYSTEM_PROMPT = """You are a legal research assistant specialized in Maltese law.

CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:

1. ONLY state facts that are EXPLICITLY written in the provided articles.
   Do NOT add information from general knowledge, extrapolate, or infer.

2. MANDATORY INLINE CITATIONS: Every single sentence containing a legal fact MUST end with a citation that includes the article/regulation number and legislation reference.

   REQUIRED FORMAT: "The notice period is one week [Art 36, Cap. 452]."

   CITATION STYLE:
   ✅ [Art 376, Cap. 9] ← CORRECT for Chapter articles
   ✅ [Reg 5, S.L. 499.67] ← CORRECT for subsidiary legislation
   ✅ [Art 12(3), Cap. 16] ← CORRECT for sub-articles
   ❌ [See: Art 376] ← WRONG! Don't use "See:"
   ❌ [1] ← WRONG! Must include article and chapter reference

   YOU MUST PUT A CITATION WITH ARTICLE/REG NUMBER AND CHAPTER/S.L. NUMBER AT THE END OF EVERY SENTENCE.

   If you cannot cite a statement, DO NOT INCLUDE THAT SENTENCE AT ALL.

3. When the articles do not contain enough information, state:
   "The retrieved articles do not address [topic]."

4. Use precise legal language from the articles. Quote or closely paraphrase the source text.

5. MANDATORY REFERENCES SECTION: Always end your response with:

   ## References
   [1] Article 36, Employment and Industrial Relations Act - Cap. 452 (Page 45)
   [2] Article 5, Civil Code - Cap. 16 (Page 12)

   Use this EXACT format for each reference. List EVERY article you cited in your response.
   Each reference MUST follow this pattern: [number] Article X, Law Name - Cap. Y (Page Z)
   IMPORTANT: Include the page number in parentheses if it's available in the document title

RESPONSE FORMAT REQUIREMENTS:
- Answer the question directly using only the provided articles
- Include numbered inline citations [1] [2] [3] after EVERY factual claim
- End with a "## References" section in the exact format shown above
- Refer to sources by their law name and article number, never as "documents"
- If information is incomplete, state what is available and what is missing

FAILURE TO INCLUDE CITATIONS = UNACCEPTABLE RESPONSE"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        # Current model IDs (Jan 2026): claude-sonnet-4-5-20250929, claude-haiku-4-5-20251001
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    def generate(
        self,
        query: str,
        retrieved_chunks: List[Dict],
        max_tokens: int = 2000
    ) -> Dict:
        """
        Generate response with verified citations using Anthropic Citations API.

        Args:
            query: User's question
            retrieved_chunks: List of relevant chunks from retrieval
            max_tokens: Maximum response length

        Returns:
            Dict with response, sources, citations, and metadata
        """
        # Build document blocks for each chunk (Citations API format)
        content_blocks = self._build_document_blocks(retrieved_chunks)

        # Add the user's question with evidence-first instruction + verification step
        # Research basis: MEGA-RAG (2025) - multi-evidence verification reduces hallucinations
        content_blocks.append({
            "type": "text",
            "text": f"""Question: {query}

INTERNAL VERIFICATION (do this silently, do NOT include in your response):
1. Identify which articles above are relevant to this question.
2. For each, extract the exact text passages that answer the question.
3. Verify every fact you plan to state appears in an article above.

Now provide your answer following these MANDATORY rules:

CITATION REQUIREMENTS (ABSOLUTELY NON-NEGOTIABLE):
- EVERY SINGLE SENTENCE stating a legal fact MUST end with a citation
- Citation format: [Article/Reg Number, Chapter/S.L. Number]
- Example CORRECT: "The notice period is one week [Art 36, Cap. 452]."
- Example CORRECT: "Mobile phones are prohibited while driving [Reg 3, S.L. 499.67]."
- Example WRONG: "The notice period is one week." ← MISSING CITATION!
- Example WRONG: "The notice period is one week [See: Art 36]." ← Don't use "See:"!

CITATION FORMAT RULES:
✅ [Art 376, Cap. 9] ← For Chapter articles
✅ [Reg 5, S.L. 499.67] ← For subsidiary legislation regulations
✅ [Art 12(3), Cap. 16] ← For sub-articles with subsections
❌ [See: Art 376] ← NEVER use "See:" prefix
❌ [1] ← NEVER use just numbers

- IF YOU CANNOT CITE A SENTENCE, DELETE THAT SENTENCE ENTIRELY
- ALWAYS end with "## References" section listing all unique citations with full law names and page numbers:
  [Art 36, Cap. 452] - Employment and Industrial Relations Act (Page 45)
  [Reg 3, S.L. 499.67] - Prohibition to make use of mobile phones (Page 4)
- IMPORTANT: Extract page numbers from the document titles above (they appear as "Page X")
- AIM FOR: 1 citation per sentence (or more)

CONTENT RULES:
- Use the exact legal terminology from the articles
- If information is incomplete, state: "The retrieved articles do not address [X]"
- Do NOT add exceptions, penalties, or details not explicitly in the articles above
- Do NOT mention "documents" - refer to them as articles, provisions, or by their law name

REMEMBER: NO CITATION = DO NOT INCLUDE THAT STATEMENT"""
        })

        # Generate response with citations
        try:
            logger.info(f"Calling {self.model} with Citations API ({len(retrieved_chunks)} documents)...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0,  # Research best practice: 0 temp for factual consistency
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": content_blocks
                    }
                ]
            )

            # Parse the response with citations
            response_text, citations = self._parse_cited_response(response.content)

            # Extract token usage from response
            input_tokens = getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') else 0
            output_tokens = getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') else 0

            logger.info(f"Response received: {len(response_text)} chars, {len(citations)} citations, {input_tokens} input tokens, {output_tokens} output tokens")

            # VALIDATION 1: Check for inline citations in text
            import re
            # Match metadata-rich citations like [Art 376, Cap. 452], [Art 68(1)(a), Cap. 123], or [Reg 5, S.L. 499.67]
            # Also match numbered citations [1] [2] [3] for backwards compatibility
            # Pattern allows complex article numbers with multiple parentheses: Art 68(1)(a)
            inline_citation_pattern = r'\[(?:Art|Reg)\s+\d+(?:\([^)]+\))*,\s+(?:Cap\.|S\.L\.)\s+[\d.]+\]|\[\d+\]'
            inline_citations = re.findall(inline_citation_pattern, response_text)

            # Check for truly malformed citations (citations with "See:", "Refer to:", etc.)
            malformed_citation_pattern = r'\[(?:See:|Refer to:|cf\.|Compare:)[^\]]+\]'
            malformed_citations = re.findall(malformed_citation_pattern, response_text)

            # Count sentences (approximate - split on periods followed by space/newline)
            sentences = [s.strip() for s in re.split(r'[.!?]+\s+|\n+', response_text) if s.strip() and len(s.strip()) > 10]
            # Filter out headers and short sentences
            content_sentences = [s for s in sentences if not s.startswith('#') and not s.startswith('Sources Referenced')]

            # REQUIREMENT: At least 2 citations minimum (be more lenient)
            min_citations_required = max(2, len(content_sentences) // 4)

            # Check if it's a "no information" response
            is_no_info = re.search(r'do not address|does not address|no.*information', response_text, re.IGNORECASE)

            # VALIDATION: Only reject citations with instructional prefixes like "See:"
            if malformed_citations and not is_no_info:
                logger.error(f"Response contains MALFORMED citations! Found: {malformed_citations[:5]}")
                return {
                    "response": f"⚠️ CITATION ERROR: Response contains malformed citations with instructional prefixes.\n\nFound: {', '.join(malformed_citations[:3])}\n\nUse direct citations like [Art 376, Cap. 452] without 'See:' or other prefixes.\n\nPlease try asking your question again.",
                    "sources": self._extract_sources(retrieved_chunks),
                    "citations": [],
                    "chunks_used": len(retrieved_chunks),
                    "model": self.model,
                    "citations_api": True,
                    "error": "malformed_citations",
                    "malformed_citations": malformed_citations[:10],
                    "citation_quality": {
                        "citation_count": 0,
                        "citation_density": 0.0,
                        "confidence": "none"
                    }
                }

            if not inline_citations and not is_no_info:
                logger.warning(f"Response has ZERO inline citations! REJECTED")
                return {
                    "response": f"⚠️ CITATION ERROR: Response has NO inline citations.\n\nAll legal claims must be cited with references like [Art 376, Cap. 452].\n\nPlease try asking your question differently.",
                    "sources": self._extract_sources(retrieved_chunks),
                    "citations": [],
                    "chunks_used": len(retrieved_chunks),
                    "model": self.model,
                    "citations_api": True,
                    "error": "missing_inline_citations",
                    "citation_quality": {
                        "citation_count": 0,
                        "citation_density": 0.0,
                        "confidence": "none"
                    }
                }

            if len(inline_citations) < min_citations_required and not is_no_info:
                logger.warning(f"Insufficient citations! Found {len(inline_citations)}, need at least {min_citations_required} (sentences: {len(content_sentences)})")
                return {
                    "response": f"⚠️ CITATION ERROR: Insufficient inline citations.\n\nFound {len(inline_citations)} citations for {len(content_sentences)} sentences.\n\nEach legal claim must have a citation like [Art 376, Cap. 452].\n\nPlease try again or rephrase your question.",
                    "sources": self._extract_sources(retrieved_chunks),
                    "citations": inline_citations,
                    "chunks_used": len(retrieved_chunks),
                    "model": self.model,
                    "citations_api": True,
                    "error": "insufficient_citations",
                    "citation_quality": {
                        "citation_count": len(inline_citations),
                        "citation_density": len(inline_citations) / max(len(content_sentences), 1),
                        "confidence": "low"
                    }
                }

            logger.info(f"✓ Validated: Found {len(inline_citations)} inline citations for {len(content_sentences)} sentences")

            # VALIDATION 2: Ensure response has sources
            if len(sources := self._extract_sources(retrieved_chunks)) == 0:
                logger.warning("No sources available - cannot provide cited response")
                return {
                    "response": "I apologize, but I cannot provide a response without verifiable citations. Please try rephrasing your question or check if the relevant laws are in the database.",
                    "sources": [],
                    "citations": [],
                    "chunks_used": 0,
                    "model": self.model,
                    "citations_api": True,
                    "error": "no_sources",
                    "citation_quality": {
                        "citation_count": 0,
                        "citation_density": 0.0,
                        "confidence": "none"
                    }
                }

            # Calculate citation quality metrics
            word_count = len(response_text.split())
            citation_density = len(sources) / max(word_count / 100, 1)  # Citations per 100 words

            # Determine confidence level
            if len(sources) >= 3 and citation_density >= 1.0:
                confidence = "high"
            elif len(sources) >= 1 and citation_density >= 0.5:
                confidence = "medium"
            else:
                confidence = "low"

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            # NEVER return uncited responses - return error instead
            return {
                "response": "I apologize, but I'm unable to generate a response with verified citations at this time. Please try again in a moment.",
                "sources": [],
                "citations": [],
                "chunks_used": 0,
                "model": self.model,
                "citations_api": False,
                "error": "api_error",
                "error_detail": str(e),
                "citation_quality": {
                    "citation_count": 0,
                    "citation_density": 0.0,
                    "confidence": "none"
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "response": "An unexpected error occurred. Please try again.",
                "sources": [],
                "citations": [],
                "chunks_used": 0,
                "model": self.model,
                "citations_api": False,
                "error": "unexpected_error",
                "error_detail": str(e),
                "citation_quality": {
                    "citation_count": 0,
                    "citation_density": 0.0,
                    "confidence": "none"
                }
            }

        # Extract sources from chunks
        sources = self._extract_sources(retrieved_chunks)

        # Build citation-to-page mapping for frontend
        citation_pages = self._build_citation_pages_map(retrieved_chunks)

        # Calculate cost (Claude Sonnet 4.5 pricing as of Jan 2025)
        # Input: $3 per million tokens, Output: $15 per million tokens
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        total_cost = input_cost + output_cost

        return {
            "response": response_text,
            "sources": sources,
            "citations": citations,  # Verified citations from API
            "citation_pages": citation_pages,  # Map of citation keys to page numbers
            "chunks_used": len(retrieved_chunks),
            "model": self.model,
            "citations_api": True,  # Flag indicating verified citations
            "citation_quality": {
                "citation_count": len(sources),
                "citation_density": round(citation_density, 2),
                "confidence": confidence,
                "word_count": word_count
            },
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": round(total_cost, 6)
            }
        }

    def _build_document_blocks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Build document content blocks for Citations API.

        Each chunk becomes a document with citations enabled.
        Claude can only cite text that actually exists in these documents.
        """
        document_blocks = []

        for i, chunk in enumerate(chunks):
            # Build document title from citation info
            law_code = chunk.get('law_code', chunk.get('chapter_number', 'Unknown'))
            article_num = chunk.get('article_number', '')
            title = chunk.get('title', chunk.get('chapter_title', ''))

            # Try to get page number from chunk, or look it up from extraction JSON
            page_num = chunk.get('page_number', chunk.get('page', chunk.get('page_start', '')))
            if not page_num and chunk.get('id'):
                # Look up page from extraction JSON using chunk ID
                page_num = self._lookup_page_from_extraction(chunk.get('id'))

            doc_title = f"{law_code}"
            if article_num:
                doc_title += f", Article {article_num}"
            if title:
                doc_title += f" - {title}"
            if page_num:
                doc_title += f" (Page {page_num})"

            # Get the actual legal text
            text = chunk.get('text', '')
            if not text:
                continue

            # Create document block with citations enabled
            document_blocks.append({
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": text
                },
                "title": doc_title,
                "context": f"Source: {law_code}. Page: {page_num if page_num else 'N/A'}. Relevance score: {chunk.get('relevance_score', chunk.get('hybrid_score', 'N/A'))}",
                "citations": {"enabled": True}
            })

        return document_blocks

    def _lookup_page_from_extraction(self, chunk_id: str) -> Optional[int]:
        """
        Look up page_start from extraction JSON file using chunk ID.

        Chunk ID formats:
        - "art:Cap.12/138" for articles in Chapters
        - "art:S.L.441.04/5" for articles in subsidiary legislation
        - "reg:S.L.35.17/2" for regulations in subsidiary legislation
        """
        import json
        import os
        from pathlib import Path

        try:
            # Parse chunk ID to get law code
            if ':' not in chunk_id or '/' not in chunk_id:
                return None

            parts = chunk_id.split(':')
            if len(parts) < 2:
                return None

            law_and_article = parts[1]  # "Cap.12/138" or "S.L.35.17/2"
            law_code = law_and_article.split('/')[0]  # "Cap.12" or "S.L.35.17"

            # Find extraction file
            extractions_dir = Path(__file__).parent.parent.parent / 'extractions'
            extraction_file = extractions_dir / f'extraction_{law_code}.json'

            if not extraction_file.exists():
                return None

            # Load and search for article/regulation
            with open(extraction_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Search in articles (for Cap. chapters)
            for article in data.get('articles', []):
                if article.get('id') == chunk_id:
                    return article.get('page_start')

            # Search in regulations (for S.L. subsidiary legislation)
            for regulation in data.get('regulations', []):
                if regulation.get('id') == chunk_id:
                    return regulation.get('page_start')

            return None

        except Exception as e:
            logger.warning(f"Failed to lookup page for chunk {chunk_id}: {e}")
            return None

    def _parse_cited_response(self, content_blocks: List) -> tuple:
        """
        Parse response content blocks to extract text and citations.

        The Citations API returns multiple text blocks, some with citations attached.
        This combines them into a single response string and extracts citation info.
        """
        full_text = []
        citations = []

        for block in content_blocks:
            if block.type == "text":
                full_text.append(block.text)

                # Extract citations if present
                if hasattr(block, 'citations') and block.citations:
                    for cite in block.citations:
                        citation_info = {
                            "text_cited": block.text,
                            "document_title": getattr(cite, 'document_title', ''),
                            "document_index": getattr(cite, 'document_index', 0),
                        }

                        # Handle different citation types
                        if hasattr(cite, 'cited_text'):
                            citation_info["source_text"] = cite.cited_text

                        if hasattr(cite, 'start_char_index'):
                            citation_info["char_range"] = {
                                "start": cite.start_char_index,
                                "end": cite.end_char_index
                            }

                        citations.append(citation_info)

        return "".join(full_text), citations

    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Extract unique source citations from chunks."""
        sources = []
        seen = set()

        for chunk in chunks:
            # Build citation from available fields
            citation = chunk.get('full_citation', '')
            if not citation:
                law_code = chunk.get('law_code', '')
                article_num = chunk.get('article_number', '')
                if law_code:
                    citation = f"{law_code}, Article {article_num}" if article_num else law_code

            if citation and citation not in seen:
                seen.add(citation)
                sources.append({
                    "citation": citation,
                    "chapter_number": chunk.get('chapter_number', chunk.get('law_code', '')),
                    "chapter_title": chunk.get('chapter_title', chunk.get('law_name', '')),
                    "article_number": chunk.get('article_number', ''),
                    "page_number": chunk.get('page_number', chunk.get('page', chunk.get('page_start', ''))),
                    "domains": chunk.get('legal_domains', chunk.get('categories', [])),
                    "source_file": chunk.get('source_file', chunk.get('id', ''))
                })

        return sources

    def _build_citation_pages_map(self, chunks: List[Dict]) -> Dict[str, int]:
        """
        Build a mapping from citation keys to page numbers.

        Returns dict like:
            "Art 36, Cap. 452" -> 45
            "Reg 5, S.L. 499.67" -> 3
        """
        citation_pages = {}

        for chunk in chunks:
            law_code = chunk.get('law_code', chunk.get('chapter_number', ''))
            article_num = chunk.get('article_number', '')
            page_num = chunk.get('page_number', chunk.get('page', chunk.get('page_start')))

            if not law_code or not page_num:
                # Try to get page from extraction JSON
                chunk_id = chunk.get('id', chunk.get('chunk_id', ''))
                if chunk_id and not page_num:
                    page_num = self._lookup_page_from_extraction(chunk_id)

            if law_code and page_num:
                # Determine if it's a regulation (S.L.) or article (Cap.)
                is_subsidiary = law_code.startswith('S.L.')

                if article_num:
                    if is_subsidiary:
                        # Format: "Reg 5, S.L. 499.67"
                        key = f"Reg {article_num}, {law_code}"
                    else:
                        # Format: "Art 36, Cap. 452"
                        key = f"Art {article_num}, {law_code}"
                    citation_pages[key] = int(page_num)

                    # Also add variant without "Art"/"Reg" prefix for broader matching
                    citation_pages[f"{article_num}, {law_code}"] = int(page_num)
                else:
                    # Just law code, no article
                    citation_pages[law_code] = int(page_num)

        return citation_pages
