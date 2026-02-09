"""
Voyage AI rerank-2 for reranking retrieved documents.
Provides significant accuracy improvement over embeddings alone.
"""

import voyageai
from typing import List, Dict
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class VoyageReranker:
    """
    Voyage AI rerank-2 reranker.
    
    - 16K token context
    - ~14% accuracy improvement over embeddings
    - Critical for legal retrieval accuracy
    """
    
    def __init__(self):
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment")
        
        self.client = voyageai.Client(api_key=api_key)
        self.model = "rerank-2"
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: The search query
            documents: List of document dicts with 'text' field
            top_k: Number of top results to return
        
        Returns:
            Reranked list of documents with relevance_score added
        """
        if not documents:
            return []
        
        # Extract texts for reranking
        texts = [doc.get('text', '') for doc in documents]
        
        # Call Voyage rerank API
        result = self.client.rerank(
            query=query,
            documents=texts,
            model=self.model,
            top_k=min(top_k, len(documents))
        )
        
        # Map results back to original documents
        reranked = []
        for item in result.results:
            doc = documents[item.index].copy()
            doc['relevance_score'] = item.relevance_score
            reranked.append(doc)
        
        logger.info(f"Reranked {len(documents)} documents, returning top {len(reranked)}")
        
        return reranked
