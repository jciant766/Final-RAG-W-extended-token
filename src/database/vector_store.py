"""
LanceDB vector store for legal chunks.
Supports metadata filtering and hybrid search.
"""

import lancedb
from lancedb.pydantic import LanceModel, Vector
from typing import List, Optional, Dict, Any
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# LanceDB schema
class LawChunkModel(LanceModel):
    chunk_id: str
    text: str
    vector: Vector(1024)  # voyage-law-2 dimension

    # Hierarchical identifiers
    chapter_number: str
    chapter_title: str
    article_number: Optional[str] = None
    sub_article_id: Optional[str] = None

    # Page metadata
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # Metadata
    full_citation: str
    context_summary: str
    cross_references: str  # JSON string
    legal_domains: str  # JSON string
    keywords: str  # JSON string
    source_file: str

class LegalVectorStore:
    """Vector store for Maltese law chunks using LanceDB."""
    
    def __init__(self, db_path: str = "./lancedb_data"):
        self.db_path = db_path
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self.table_name = "maltese_law"
        self.table = None
    
    def create_table(self, overwrite: bool = False):
        """Create the chunks table."""
        if self.table_name in self.db.table_names():
            if overwrite:
                self.db.drop_table(self.table_name)
                logger.info(f"Dropped existing table: {self.table_name}")
            else:
                self.table = self.db.open_table(self.table_name)
                logger.info(f"Opened existing table: {self.table_name}")
                return
        
        # Create empty table with schema
        self.table = self.db.create_table(
            self.table_name,
            schema=LawChunkModel
        )
        logger.info(f"Created new table: {self.table_name}")
    
    def add_chunks(self, chunks: List['LegalChunk'], embeddings: List[List[float]]):
        """Add chunks with their embeddings to the store."""
        if self.table is None:
            self.create_table()
        
        records = []
        for chunk, embedding in zip(chunks, embeddings):
            record = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "vector": embedding,
                "chapter_number": chunk.chapter_number,
                "chapter_title": chunk.chapter_title,
                "article_number": chunk.article_number,
                "sub_article_id": chunk.sub_article_id,
                "page_start": getattr(chunk, 'page_start', None),
                "page_end": getattr(chunk, 'page_end', None),
                "full_citation": chunk.full_citation,
                "context_summary": chunk.context_summary,
                "cross_references": json.dumps(chunk.cross_references),
                "legal_domains": json.dumps(chunk.legal_domains),
                "keywords": json.dumps(chunk.keywords),
                "source_file": chunk.source_file,
            }
            records.append(record)
        
        self.table.add(records)
        logger.info(f"Added {len(records)} chunks to vector store")
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 20,
        chapter_filter: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        if self.table is None:
            self.table = self.db.open_table(self.table_name)
        
        # Build search
        search = self.table.search(query_embedding)
        
        # Apply filters
        filters = []
        if chapter_filter:
            filters.append(f"chapter_number = '{chapter_filter}'")
        if domain_filter:
            filters.append(f"legal_domains LIKE '%{domain_filter}%'")
        
        if filters:
            where_clause = " AND ".join(filters)
            search = search.where(where_clause)
        
        # Execute
        results = search.limit(limit).to_pandas()
        
        # Convert to list of dicts
        records = results.to_dict('records')
        
        # Parse JSON fields
        for record in records:
            record['cross_references'] = json.loads(record.get('cross_references', '[]'))
            record['legal_domains'] = json.loads(record.get('legal_domains', '[]'))
            record['keywords'] = json.loads(record.get('keywords', '[]'))
        
        return records
    
    def get_all_texts(self) -> List[Dict[str, str]]:
        """Get all texts and IDs for BM25 indexing."""
        if self.table is None:
            self.table = self.db.open_table(self.table_name)
        
        df = self.table.to_pandas()
        return [
            {"chunk_id": row['chunk_id'], "text": row['text']}
            for _, row in df.iterrows()
        ]
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Get a specific chunk by ID."""
        if self.table is None:
            self.table = self.db.open_table(self.table_name)
        
        results = self.table.search().where(f"chunk_id = '{chunk_id}'").limit(1).to_pandas()
        
        if len(results) == 0:
            return None
        
        record = results.iloc[0].to_dict()
        record['cross_references'] = json.loads(record.get('cross_references', '[]'))
        record['legal_domains'] = json.loads(record.get('legal_domains', '[]'))
        record['keywords'] = json.loads(record.get('keywords', '[]'))
        
        return record
    
    def count(self) -> int:
        """Get total number of chunks."""
        if self.table is None:
            try:
                self.table = self.db.open_table(self.table_name)
            except Exception:
                return 0
        return self.table.count_rows()
