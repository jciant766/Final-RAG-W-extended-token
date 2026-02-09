"""
Enhanced retrieval pipeline with research-backed improvements.

Provides multi-query expansion, relevance filtering, and definition boosting
as composable functions that work with any retriever.

Research basis:
- Multi-query RAG: 7-14% recall improvement (MQRF-RAG 2025)
- Reranking with threshold: 28-48% precision improvement (Pinecone 2025)
- Definition article boosting: Covers implicit terminology questions
"""

import anthropic
from typing import List, Dict, Optional, Callable
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EnhancedRetrievalPipeline:
    """
    Wraps a retriever with multi-query, reranking+threshold, and definition boosting.

    Works with both HybridRetriever and GraphRAGRetriever.
    """

    def __init__(self, reranker=None):
        """
        Args:
            reranker: VoyageReranker instance (optional, falls back to score-based ordering)
        """
        self.reranker = reranker
        self._anthropic_client = None

    @property
    def anthropic_client(self):
        """Lazy-init Anthropic client for multi-query generation."""
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.Anthropic()
        return self._anthropic_client

    def generate_query_variants(self, query: str, num_variants: int = 2) -> List[str]:
        """
        Generate alternative query phrasings for multi-query retrieval.

        Args:
            query: Original user query
            num_variants: Number of alternatives to generate (default 2)

        Returns:
            List of queries including original (max num_variants + 1)
        """
        try:
            response = self.anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"""Generate {num_variants} alternative phrasings of this legal query for Malta law search. Each should capture the same intent but use different keywords/structure.

Query: {query}

Output ONLY the {num_variants} alternatives, one per line. No numbering, no explanation."""
                }]
            )

            variants = [query]  # Always include original
            for line in response.content[0].text.strip().split('\n'):
                line = line.strip()
                if line and len(line) > 10:
                    variants.append(line)

            logger.info(f"Multi-query: generated {len(variants)} variants")
            return variants[:num_variants + 1]

        except Exception as e:
            logger.warning(f"Multi-query generation failed: {e}")
            return [query]

    def rerank_and_filter(
        self,
        query: str,
        articles: List[Dict],
        top_k: int = 5,
        min_relevance: float = 0.25
    ) -> List[Dict]:
        """
        Rerank articles and drop those below relevance threshold.

        Args:
            query: User query
            articles: Retrieved articles with 'text' field
            top_k: Max articles to return
            min_relevance: Minimum relevance score (Voyage rerank-2 scale)

        Returns:
            Top-k articles above threshold, reranked by relevance
        """
        if not self.reranker or not articles:
            return articles[:top_k]

        try:
            reranked = self.reranker.rerank(query, articles, top_k=len(articles))

            # Filter by threshold
            filtered = [a for a in reranked if a.get('relevance_score', 1.0) >= min_relevance]

            dropped = len(reranked) - len(filtered)
            if dropped > 0:
                logger.info(f"Relevance filter: dropped {dropped} articles below {min_relevance}")

            return filtered[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed: {e}, using original order")
            return articles[:top_k]

    def boost_definition_articles(
        self,
        articles: List[Dict],
        fetch_article_fn: Callable[[str, str], Optional[Dict]]
    ) -> List[Dict]:
        """
        Append definition article (Article 2 or 3) from the primary law if relevant.

        Only adds ONE definition article from the PRIMARY law (highest-ranked),
        and only if it contains interpretation/definition keywords.

        Args:
            articles: Current article list (already ranked)
            fetch_article_fn: Callable(law_code, article_number) -> article dict or None

        Returns:
            Articles with definition article appended (if found)
        """
        if not articles:
            return articles

        # Check existing articles
        existing = set(
            (a.get('law_code', ''), a.get('article_number', ''))
            for a in articles
        )

        # Only boost from primary law
        primary_law = articles[0].get('law_code', '')
        if not primary_law:
            return articles

        for def_art_num in ['2', '3']:
            if (primary_law, def_art_num) in existing:
                continue

            def_article = fetch_article_fn(primary_law, def_art_num)
            if not def_article:
                continue

            title = (def_article.get('title') or '').lower()
            text = (def_article.get('text') or '').lower()[:500]
            if any(term in title or term in text for term in
                   ['interpretation', 'definition', 'meaning', 'shall mean']):
                def_article['_boosted'] = True
                logger.info(f"Boosted definition article: {primary_law} Article {def_art_num}")
                return articles + [def_article]

        return articles
