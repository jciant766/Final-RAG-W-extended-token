"""
Voyage AI embeddings using voyage-law-2.
Best-in-class legal embedding model.
"""

import voyageai
from typing import List, Optional
import os
import time
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # seconds
MAX_BACKOFF = 60  # seconds

class VoyageEmbeddings:
    """
    Voyage AI voyage-law-2 embeddings.
    
    - Optimized for legal retrieval
    - 1024 dimensions
    - 16K token context
    - Supports query/document input types for asymmetric search
    """
    
    def __init__(self):
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment")
        
        self.client = voyageai.Client(api_key=api_key)
        self.model = "voyage-law-2"
        self.dimension = 1024
    
    def _embed_with_retry(self, texts: List[str], input_type: str) -> List[List[float]]:
        """
        Embed texts with exponential backoff retry on connection errors.
        """
        backoff = INITIAL_BACKOFF
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                result = self.client.embed(
                    texts=texts,
                    model=self.model,
                    input_type=input_type
                )
                return result.embeddings
            except (ConnectionError, ConnectionResetError, voyageai.error.APIConnectionError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                else:
                    logger.error(f"Max retries reached, giving up: {e}")
                    raise
            except Exception as e:
                # For other errors, check if it's a connection-related error in the message
                error_str = str(e).lower()
                if "connection" in error_str or "reset" in error_str or "aborted" in error_str:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {backoff}s: {e}")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                    else:
                        logger.error(f"Max retries reached, giving up: {e}")
                        raise
                else:
                    raise

        raise last_error

    def embed_documents(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Embed documents for storage.
        Uses input_type="document" for asymmetric retrieval.
        Includes retry logic for connection errors.
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            embeddings = self._embed_with_retry(batch, "document")
            all_embeddings.extend(embeddings)

            if i % 100 == 0 and i > 0:
                logger.info(f"Embedded {i}/{len(texts)} documents")

        return all_embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query for search.
        Uses input_type="query" for asymmetric retrieval.
        """
        embeddings = self._embed_with_retry([query], "query")
        return embeddings[0]

    def embed_queries(self, queries: List[str]) -> List[List[float]]:
        """Embed multiple queries."""
        return self._embed_with_retry(queries, "query")
