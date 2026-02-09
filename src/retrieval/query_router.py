"""
LLM-based query analysis using Claude Haiku via OpenRouter.

Extracts key concepts and chapter hints to improve retrieval.
Note: Domain-based routing has been replaced with chapter-level semantic routing
in the HybridRetriever using the ChapterIndex.
"""

import os
from openai import OpenAI
from typing import Dict, List, Optional
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Uses Claude Haiku to analyze queries and extract:
    - Specific chapter references mentioned by user
    - Key legal concepts for query expansion
    - Query type classification

    Note: Domain routing is deprecated. Chapter-level semantic routing
    is now handled by ChapterIndex in the HybridRetriever.
    """

    SYSTEM_PROMPT = """You are a legal query analyzer for Maltese law.
Your job is to analyze user queries and extract information to improve legal document retrieval.

Respond ONLY with a valid JSON object, no other text."""

    USER_PROMPT_TEMPLATE = """Analyze this legal query and extract:
1. chapter_hints: Any specific chapter numbers or law names mentioned (empty list if none)
   Examples: "Chapter 386", "Companies Act", "Chapter 18" -> extract the numbers
2. key_concepts: Important legal terms/concepts to search for (3-5 terms)
   These should be synonyms or related terms that might appear in the law
3. query_type: "specific" (asking about specific law), "general" (exploring topic), or "comparative" (comparing laws)

Query: {query}

JSON response:"""

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = "anthropic/claude-3.5-haiku"  # Fast and cheap for routing

    def analyze_query(self, query: str) -> Dict:
        """Analyze query and extract routing information."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": self.USER_PROMPT_TEMPLATE.format(query=query)}
                ],
                max_tokens=300,
                temperature=0
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            result = json.loads(content)

            logger.info(f"Query analysis: {result}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse routing response: {e}")
            return self._default_analysis()
        except Exception as e:
            logger.warning(f"Query routing failed: {e}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict:
        """Return default analysis when routing fails."""
        return {
            "chapter_hints": [],
            "key_concepts": [],
            "query_type": "general"
        }

    def get_search_parameters(self, query: str) -> Dict:
        """Get search parameters from query analysis."""
        analysis = self.analyze_query(query)

        params = {
            "original_query": query,
            "chapter_filter": None,
            "enhanced_query": query
        }

        # Set chapter filter if specific chapter mentioned
        if analysis.get("chapter_hints"):
            # Extract numeric chapter hints
            chapter_hints = []
            for hint in analysis["chapter_hints"]:
                # Try to extract number from hint
                if isinstance(hint, (int, float)):
                    chapter_hints.append(str(int(hint)))
                elif isinstance(hint, str):
                    # Extract digits from string like "Chapter 386" or "386"
                    import re
                    numbers = re.findall(r'\d+', str(hint))
                    if numbers:
                        chapter_hints.append(numbers[0])

            if chapter_hints:
                params["chapter_filter"] = chapter_hints

        # Enhance query with key concepts
        if analysis.get("key_concepts"):
            concepts = " ".join(analysis["key_concepts"])
            params["enhanced_query"] = f"{query} {concepts}"

        params["analysis"] = analysis

        return params

    def expand_query(self, query: str) -> str:
        """
        Simple query expansion using key concepts.
        Returns enhanced query string.
        """
        params = self.get_search_parameters(query)
        return params.get("enhanced_query", query)
