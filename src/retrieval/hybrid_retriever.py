"""
Hybrid retrieval combining BM25 keyword search and vector semantic search.
Uses Reciprocal Rank Fusion (RRF) to merge results.

Supports chapter-based filtering for efficient query routing.
"""

from rank_bm25 import BM25Okapi
from typing import List, Dict, Optional, Tuple, Union
import numpy as np
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines BM25 (keyword) and vector (semantic) search.
    Critical for legal documents where exact terms matter alongside meaning.

    Supports filtering by:
    - Single chapter: chapter_filter="386"
    - Multiple chapters: chapter_filter=["386", "9", "213"]
    """

    def __init__(self, vector_store, embedder, chapter_index=None):
        self.vector_store = vector_store
        self.embedder = embedder
        self.chapter_index = chapter_index  # Optional ChapterIndex for routing
        self.bm25 = None
        self.corpus = []
        self.chunk_ids = []
        self.chunk_lookup = {}
        self.chunk_chapters = {}  # Map chunk_id -> chapter_number for filtering
    
    def build_bm25_index(self):
        """Build BM25 index from all chunks in vector store."""
        logger.info("Building BM25 index...")

        all_docs = self.vector_store.get_all_texts()

        self.corpus = [doc['text'] for doc in all_docs]
        self.chunk_ids = [doc['chunk_id'] for doc in all_docs]

        # Build lookup and chapter mapping
        for doc in all_docs:
            self.chunk_lookup[doc['chunk_id']] = doc
            # Store chapter mapping for filtering
            if 'chapter_number' in doc:
                self.chunk_chapters[doc['chunk_id']] = doc['chapter_number']

        # Tokenize for BM25
        tokenized_corpus = [self._tokenize(doc) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

        logger.info(f"BM25 index built with {len(self.corpus)} documents")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Lowercase and split on non-alphanumeric
        import re
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def search(
        self,
        query: str,
        limit: int = 20,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        chapter_filter: Optional[Union[str, List[str]]] = None,
        domain_filter: Optional[str] = None,
        use_chapter_routing: bool = False,
        top_chapters: int = 10
    ) -> List[Dict]:
        """
        Perform hybrid search with RRF fusion.

        Args:
            query: Search query
            limit: Number of results to return
            vector_weight: Weight for vector search in RRF
            bm25_weight: Weight for BM25 in RRF
            chapter_filter: Optional chapter filter - can be single string or list
            domain_filter: Optional domain filter (deprecated, kept for compatibility)
            use_chapter_routing: If True, use chapter index to find relevant chapters first
            top_chapters: Number of top chapters to use when routing

        Returns:
            List of chunk dictionaries with scores
        """
        # If chapter routing enabled and we have an index, find relevant chapters
        if use_chapter_routing and self.chapter_index and not chapter_filter:
            query_embedding = self.embedder.embed_query(query)
            chapter_filter = self.chapter_index.get_chapter_numbers(
                query_embedding, limit=top_chapters
            )
            logger.info(f"Chapter routing: searching in {len(chapter_filter)} chapters")

        # Normalize chapter_filter to list
        if chapter_filter and isinstance(chapter_filter, str):
            chapter_filter = [chapter_filter]

        # Get more results for fusion
        fetch_limit = limit * 3

        # Vector search
        query_embedding = self.embedder.embed_query(query)

        # For vector search, we'll search broadly then filter
        # (LanceDB supports single chapter filter, so we filter after for multiple)
        vector_results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=fetch_limit * 2 if chapter_filter else fetch_limit,
            chapter_filter=None,  # We'll filter manually for multi-chapter
            domain_filter=domain_filter
        )

        # BM25 search
        bm25_results = self._bm25_search(query, fetch_limit * 2 if chapter_filter else fetch_limit)

        # Apply chapter filter to both result sets before fusion
        if chapter_filter:
            vector_results = [
                r for r in vector_results
                if r.get('chapter_number') in chapter_filter
            ][:fetch_limit]

            bm25_results = [
                (cid, score) for cid, score in bm25_results
                if self.chunk_chapters.get(cid) in chapter_filter
            ][:fetch_limit]

        # Fuse with RRF
        fused = self._reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight
        )

        return fused[:limit]

    def search_with_routing(
        self,
        query: str,
        limit: int = 20,
        top_chapters: int = 10,
        **kwargs
    ) -> Tuple[List[Dict], List[str]]:
        """
        Search with automatic chapter routing.

        Returns:
            Tuple of (results, chapter_numbers_searched)
        """
        if not self.chapter_index:
            logger.warning("No chapter index available, searching all chapters")
            return self.search(query, limit, **kwargs), []

        # Get relevant chapters
        query_embedding = self.embedder.embed_query(query)
        chapter_numbers = self.chapter_index.get_chapter_numbers(
            query_embedding, limit=top_chapters
        )

        # Search within those chapters
        results = self.search(
            query=query,
            limit=limit,
            chapter_filter=chapter_numbers,
            **kwargs
        )

        return results, chapter_numbers
    
    def _bm25_search(self, query: str, limit: int) -> List[Tuple[str, float]]:
        """Perform BM25 search."""
        if self.bm25 is None:
            logger.warning("BM25 index not built")
            return []
        
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top results
        top_indices = np.argsort(scores)[::-1][:limit]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.chunk_ids[idx], float(scores[idx])))
        
        return results
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Tuple[str, float]],
        vector_weight: float,
        bm25_weight: float,
        k: int = 60
    ) -> List[Dict]:
        """
        Merge results using Reciprocal Rank Fusion.
        RRF score = sum(weight / (k + rank))
        """
        scores = {}
        result_data = {}
        
        # Process vector results
        for rank, result in enumerate(vector_results):
            chunk_id = result['chunk_id']
            rrf_score = vector_weight / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
            result_data[chunk_id] = result
        
        # Process BM25 results
        for rank, (chunk_id, bm25_score) in enumerate(bm25_results):
            rrf_score = bm25_weight / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
            
            # Add to result_data if not present
            if chunk_id not in result_data:
                chunk_data = self.vector_store.get_chunk_by_id(chunk_id)
                if chunk_data:
                    result_data[chunk_id] = chunk_data
        
        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # Build final results
        final_results = []
        for chunk_id in sorted_ids:
            if chunk_id in result_data:
                result = result_data[chunk_id].copy()
                result['hybrid_score'] = scores[chunk_id]
                final_results.append(result)
        
        return final_results
