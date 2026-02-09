"""
Chapter-level index for fast query routing.

Stores summaries and embeddings for each law chapter, enabling
fast semantic search across 600+ laws before drilling into chunks.
"""

import lancedb
from lancedb.pydantic import LanceModel, Vector
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChapterSummaryModel(LanceModel):
    """Schema for chapter summary table."""
    chapter_number: str
    chapter_title: str
    summary: str
    summary_embedding: Vector(1024)  # voyage-law-2 dimension
    num_articles: int
    source_file: str


class ChapterIndex:
    """
    Lightweight index of chapter summaries for fast query routing.

    Use cases:
    - Search 600 chapter summaries in ~50ms
    - Return top 5-10 relevant chapters
    - Filter main chunk search to those chapters only
    """

    def __init__(self, db_path: str = "./lancedb_data"):
        self.db_path = db_path
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self.table_name = "chapter_summaries"
        self.table = None

    def create_table(self, overwrite: bool = False):
        """Create or open the chapter summaries table."""
        if self.table_name in self.db.table_names():
            if overwrite:
                self.db.drop_table(self.table_name)
                logger.info(f"Dropped existing table: {self.table_name}")
            else:
                self.table = self.db.open_table(self.table_name)
                logger.info(f"Opened existing table: {self.table_name}")
                return

        self.table = self.db.create_table(
            self.table_name,
            schema=ChapterSummaryModel
        )
        logger.info(f"Created new table: {self.table_name}")

    def add_chapter(
        self,
        chapter_number: str,
        chapter_title: str,
        summary: str,
        summary_embedding: List[float],
        num_articles: int,
        source_file: str
    ):
        """Add a single chapter summary to the index."""
        if self.table is None:
            self.create_table()

        record = {
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "summary": summary,
            "summary_embedding": summary_embedding,
            "num_articles": num_articles,
            "source_file": source_file
        }
        self.table.add([record])
        logger.debug(f"Added chapter {chapter_number}: {chapter_title}")

    def add_chapters_batch(self, chapters: List[Dict[str, Any]]):
        """Add multiple chapter summaries at once."""
        if self.table is None:
            self.create_table()

        self.table.add(chapters)
        logger.info(f"Added {len(chapters)} chapters to index")

    def search_chapters(
        self,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for most relevant chapters by summary similarity.

        Args:
            query_embedding: Embedded query vector (1024 dim)
            limit: Number of top chapters to return

        Returns:
            List of chapter dicts with chapter_number, title, summary, score
        """
        if self.table is None:
            try:
                self.table = self.db.open_table(self.table_name)
            except Exception as e:
                logger.error(f"Could not open chapter index: {e}")
                return []

        results = self.table.search(query_embedding).limit(limit).to_pandas()

        records = results.to_dict('records')

        # Add distance as score (lower is better, so we invert for display)
        for record in records:
            if '_distance' in record:
                record['score'] = 1 / (1 + record['_distance'])
            else:
                record['score'] = 0.0

        return records

    def get_chapter_numbers(
        self,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[str]:
        """
        Get just the chapter numbers for top matching chapters.

        This is the main method for query routing - returns chapter numbers
        to use as filters for the main chunk search.
        """
        results = self.search_chapters(query_embedding, limit)
        return [r['chapter_number'] for r in results]

    def get_all_chapters(self) -> List[Dict[str, Any]]:
        """Get all chapters for display/admin purposes."""
        if self.table is None:
            try:
                self.table = self.db.open_table(self.table_name)
            except Exception:
                return []

        df = self.table.to_pandas()
        # Exclude the embedding column for display
        if 'summary_embedding' in df.columns:
            df = df.drop(columns=['summary_embedding'])
        return df.to_dict('records')

    def get_chapter_by_number(self, chapter_number: str) -> Optional[Dict[str, Any]]:
        """Get a specific chapter by its number."""
        if self.table is None:
            try:
                self.table = self.db.open_table(self.table_name)
            except Exception:
                return None

        results = self.table.search().where(
            f"chapter_number = '{chapter_number}'"
        ).limit(1).to_pandas()

        if len(results) == 0:
            return None

        record = results.iloc[0].to_dict()
        if 'summary_embedding' in record:
            del record['summary_embedding']
        return record

    def count(self) -> int:
        """Get total number of chapters indexed."""
        if self.table is None:
            try:
                self.table = self.db.open_table(self.table_name)
            except Exception:
                return 0
        return self.table.count_rows()

    def delete_chapter(self, chapter_number: str):
        """Delete a chapter from the index."""
        if self.table is None:
            return

        self.table.delete(f"chapter_number = '{chapter_number}'")
        logger.info(f"Deleted chapter {chapter_number} from index")
