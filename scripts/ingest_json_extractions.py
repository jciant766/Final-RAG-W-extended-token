#!/usr/bin/env python3
"""
Ingestion pipeline for pre-extracted Maltese law JSON files.

This script ingests the Graph RAG formatted extraction JSONs into LanceDB:
1. Law summaries - One vector per law with summary text
2. Articles - Each article/regulation with combined sub-items as one vector
3. Schedules - Each schedule as a vector (combines sections into text)
4. Miscellaneous - Tariffs, forms, tables and other legal content
5. Edges - Cross-references stored separately for graph traversal

The extraction JSONs already have proper Graph RAG IDs (e.g., art:Cap.1/3).

Run: python scripts/ingest_json_extractions.py extractions/
     python scripts/ingest_json_extractions.py extractions/ --overwrite
"""

import sys
import os
from pathlib import Path
import json
from tqdm import tqdm
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings.voyage_embeddings import VoyageEmbeddings

import lancedb
from lancedb.pydantic import LanceModel, Vector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# LanceDB Schema Definitions (Graph RAG Format)
# ============================================================================

class LawSummaryModel(LanceModel):
    """Law summary vectors for initial filtering."""
    id: str  # law:Cap.1 or law:S.L.441.04
    type: str  # "law_summary"
    text: str  # Summary text for embedding
    vector: Vector(1024)  # voyage-law-2

    # Metadata
    law_code: str  # Cap. 1 or S.L. 441.04
    law_name: str
    law_type: str  # "chapter" or "subsidiary"
    parent_code: Optional[str] = None
    categories: str  # JSON array
    key_topics: str  # JSON array
    total_articles: int
    total_schedules: int

    # Edges as JSON (for graph traversal)
    edges_json: str  # JSON with references_laws, children, etc.


class ArticleModel(LanceModel):
    """Article vectors with combined sub-items."""
    id: str  # art:Cap.1/3 or art:S.L.441.04/5
    type: str  # "article"
    text: str  # Full article text with sub-items
    vector: Vector(1024)

    # Metadata
    law_code: str
    law_name: str
    article_number: str  # "3" or "5A"
    title: Optional[str] = None
    sub_items: str  # JSON array of sub-item identifiers
    sub_items_count: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    categories: str  # JSON array (inherited from law)

    # Edges as JSON
    edges_json: str  # JSON with internal/external references


class ScheduleModel(LanceModel):
    """Schedule vectors."""
    id: str  # sched:Cap.1/First or sched:S.L.441.04/A
    type: str  # "schedule"
    text: str
    vector: Vector(1024)

    # Metadata
    law_code: str
    law_name: str
    schedule_name: str
    title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    categories: str  # JSON array


class MiscellaneousModel(LanceModel):
    """Miscellaneous content vectors (tariffs, forms, tables)."""
    id: str  # misc:Cap.12/page/303
    type: str  # "miscellaneous"
    text: str
    vector: Vector(1024)

    # Metadata
    law_code: str
    law_name: str
    page: Optional[int] = None
    extraction_method: Optional[str] = None
    categories: str  # JSON array


class EdgeModel(LanceModel):
    """Graph edges for cross-reference traversal."""
    id: str  # Unique edge ID
    source_id: str  # art:Cap.1/3
    target_id: str  # art:Cap.1/2 or art:Cap.12/627
    edge_type: str  # INTERNAL_REF, EXTERNAL_REF, CITES
    source_type: str  # "article", "schedule"
    target_type: str  # "article", "law", "schedule"
    target_law: Optional[str] = None  # For external refs
    sub_target: Optional[str] = None  # For sub-article refs


# ============================================================================
# Data Classes for Processing
# ============================================================================

@dataclass
class ProcessedLaw:
    """Processed law data ready for embedding."""
    law_id: str
    law_code: str
    law_name: str
    law_type: str
    summary_text: str
    categories: List[str]
    key_topics: List[str]
    articles: List[Dict]
    schedules: List[Dict]
    miscellaneous: List[Dict]  # Tariffs, forms, tables
    edges: List[Dict]


# ============================================================================
# Ingestion Functions
# ============================================================================

def load_extraction(file_path: Path) -> Optional[Dict]:
    """Load and validate an extraction JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate required fields - must have law_code
        if not data.get('law_code'):
            logger.warning(f"Missing law_code in {file_path.name} - skipping")
            return None

        # Check for malformed files (old extraction format or debug files)
        # These have keys like 'model', 'document', 'cap' instead of proper structure
        malformed_keys = {'model', 'document', 'cap', 'pages_processed', 'fewshot_examples_used', 'page_results'}
        if malformed_keys & set(data.keys()):
            logger.warning(f"Malformed extraction format in {file_path.name} - skipping")
            return None

        # Handle null metadata - create empty dict instead
        if data.get('metadata') is None:
            logger.info(f"Null metadata in {file_path.name}, using defaults")
            data['metadata'] = {}

        return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {file_path.name}: {e}")
        return None


def create_law_id(law_code: str) -> str:
    """Create Graph RAG law ID from law code."""
    # Cap. 1 -> law:Cap.1
    # S.L. 441.04 -> law:S.L.441.04
    normalized = law_code.replace(" ", "").replace(".", "")
    if law_code.startswith("Cap"):
        num = law_code.split()[-1]
        return f"law:Cap.{num}"
    elif law_code.startswith("S.L"):
        num = law_code.replace("S.L.", "").strip()
        return f"law:S.L.{num}"
    return f"law:{normalized}"


def build_article_text(article: Dict) -> str:
    """Build full article text including sub-items."""
    parts = []

    # Article header
    number = article.get('number', '')
    title = article.get('title', '')
    if title:
        parts.append(f"Article {number} - {title}")
    else:
        parts.append(f"Article {number}")

    # Main text
    main_text = article.get('text', '')
    if main_text:
        parts.append(main_text)

    # Sub-items (if any) - can be list of dicts OR list of strings
    sub_items = article.get('sub_items', [])
    for sub in sub_items:
        if isinstance(sub, dict):
            # Dict format: {"id": "...", "text": "..."}
            sub_id = sub.get('id', '')
            sub_text = sub.get('text', '')
            if sub_text:
                # Extract sub-item identifier (e.g., "(1)(a)")
                if '/' in sub_id:
                    sub_label = sub_id.split('/')[-1].replace(number, '')
                else:
                    sub_label = sub_id
                parts.append(f"[{sub_label}] {sub_text}")
        elif isinstance(sub, str):
            # String format: just the identifier like "41(1)"
            # Text is already in main article text, just note the sub-item exists
            pass  # Sub-item text is embedded in main text

    return "\n\n".join(parts)


def get_sub_item_ids(article: Dict) -> List[str]:
    """Extract sub-item identifiers from an article."""
    sub_items = article.get('sub_items', [])
    ids = [article.get('number', '')]
    for sub in sub_items:
        if isinstance(sub, dict):
            sub_id = sub.get('id', '')
            if '/' in sub_id:
                # Extract just the identifier part (e.g., "5(1)(a)" from "art:Cap.1/5(1)(a)")
                ids.append(sub_id.split('/')[-1])
            elif sub_id:
                ids.append(sub_id)
        elif isinstance(sub, str):
            # String format: just the identifier like "41(1)"
            ids.append(sub)
    return ids


def process_extraction(data: Dict) -> ProcessedLaw:
    """Process an extraction JSON into structured data."""
    law_code = data['law_code']
    law_id = create_law_id(law_code)
    metadata = data.get('metadata', {}) or {}  # Handle None metadata

    # Get summary text
    summary_text = metadata.get('summary_text', '')
    if not summary_text:
        # Fallback to purpose + scope
        purpose = metadata.get('purpose', '')
        scope = metadata.get('scope', '')
        summary_text = f"{purpose} {scope}".strip()
    if not summary_text:
        summary_text = f"{data.get('law_name', '')} - Maltese legislation."

    # IMPORTANT: Combine both 'articles' (for Chapters) AND 'regulations' (for S.L.)
    # They have the same structure, just different keys
    articles = data.get('articles', []) or []
    regulations = data.get('regulations', []) or []
    all_articles = articles + regulations

    return ProcessedLaw(
        law_id=law_id,
        law_code=law_code,
        law_name=data.get('law_name', ''),
        law_type=data.get('law_type', 'unknown'),
        summary_text=summary_text,
        categories=metadata.get('categories', []) or [],
        key_topics=metadata.get('key_topics', []) or [],
        articles=all_articles,  # Combined articles + regulations
        schedules=data.get('schedules', []) or [],
        miscellaneous=data.get('miscellaneous', []) or [],  # Tariffs, forms, tables
        edges=data.get('edges', []) or []
    )


def ingest_extractions(
    extractions_dir: str,
    db_path: str = "./lancedb_graphrag",
    batch_size: int = 20,
    overwrite: bool = False
):
    """
    Ingest all extraction JSONs into LanceDB.

    Args:
        extractions_dir: Path to extractions directory
        db_path: Path for LanceDB database
        batch_size: Batch size for embeddings
        overwrite: Whether to overwrite existing tables
    """
    extractions_path = Path(extractions_dir)
    if not extractions_path.exists():
        logger.error(f"Directory not found: {extractions_dir}")
        return

    # Find all extraction files
    json_files = list(extractions_path.glob("extraction_*.json"))
    logger.info(f"Found {len(json_files)} extraction files")

    if not json_files:
        logger.warning("No extraction files found!")
        return

    # Initialize embedder
    logger.info("Initializing Voyage embeddings...")
    embedder = VoyageEmbeddings()

    # Initialize LanceDB
    logger.info(f"Connecting to LanceDB at {db_path}...")
    Path(db_path).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(db_path)

    # Create tables
    table_names = db.table_names()

    def create_or_open_table(name: str, schema):
        if name in table_names:
            if overwrite:
                db.drop_table(name)
                logger.info(f"Dropped existing table: {name}")
                return db.create_table(name, schema=schema)
            else:
                return db.open_table(name)
        return db.create_table(name, schema=schema)

    law_summaries_table = create_or_open_table("law_summaries", LawSummaryModel)
    articles_table = create_or_open_table("articles", ArticleModel)
    schedules_table = create_or_open_table("schedules", ScheduleModel)
    miscellaneous_table = create_or_open_table("miscellaneous", MiscellaneousModel)
    edges_table = create_or_open_table("edges", EdgeModel)

    # Statistics
    stats = {
        "total_files": len(json_files),
        "successful": 0,
        "failed": 0,
        "total_laws": 0,
        "total_articles": 0,
        "total_schedules": 0,
        "total_miscellaneous": 0,
        "total_edges": 0,
        "failed_files": []
    }

    # Collect all data for batch embedding
    all_law_summaries = []
    all_articles = []
    all_schedules = []
    all_miscellaneous = []
    all_edges = []

    # Process each extraction
    logger.info("Processing extraction files...")
    for json_file in tqdm(json_files, desc="Loading extractions"):
        try:
            data = load_extraction(json_file)
            if not data:
                stats["failed"] += 1
                stats["failed_files"].append({"file": json_file.name, "reason": "invalid_json"})
                continue

            processed = process_extraction(data)

            # Law summary - include key_topics AND relation_to_parent for better semantic matching
            embedding_text = processed.summary_text

            # Add relation_to_parent for subsidiary legislation (critical for finding relevant S.L. laws)
            relation_to_parent = data.get('metadata', {}).get('relation_to_parent')
            if relation_to_parent:
                embedding_text = f"{embedding_text}\n\nRelation to parent law: {relation_to_parent}"

            if processed.key_topics:
                topics_str = ", ".join(processed.key_topics)
                embedding_text = f"{embedding_text}\n\nKey topics: {topics_str}"

            all_law_summaries.append({
                "id": processed.law_id,
                "type": "law_summary",
                "text": embedding_text,
                "law_code": processed.law_code,
                "law_name": processed.law_name,
                "law_type": processed.law_type,
                "parent_code": data.get('metadata', {}).get('parent_code'),
                "categories": json.dumps(processed.categories),
                "key_topics": json.dumps(processed.key_topics),
                "total_articles": len(processed.articles),
                "total_schedules": len(processed.schedules),
                "edges_json": json.dumps({
                    "references_laws": [e.get('target_law') for e in processed.edges if e.get('target_law')]
                })
            })

            # Articles
            for article in processed.articles:
                article_id = article.get('id', '')
                if not article_id:
                    continue

                article_text = build_article_text(article)
                sub_ids = get_sub_item_ids(article)

                # Build article edges (handle both string and dict formats)
                cross_refs = article.get('cross_references', {}) or {}
                internal_refs = []
                for r in cross_refs.get('internal', []) or []:
                    if isinstance(r, str):
                        # String format: just article number like "54A"
                        internal_refs.append(f"art:{processed.law_code.replace(' ', '')}/{r}")
                    elif isinstance(r, dict) and r.get('target_id'):
                        internal_refs.append(r['target_id'])

                external_refs = []
                for r in cross_refs.get('external', []) or []:
                    if isinstance(r, dict):
                        if r.get('target_id'):
                            external_refs.append(r['target_id'])
                        elif r.get('law'):
                            # Format: {"law": "...", "article": ...}
                            external_refs.append(r['law'])

                all_articles.append({
                    "id": article_id,
                    "type": "article",
                    "text": article_text,
                    "law_code": processed.law_code,
                    "law_name": processed.law_name,
                    "article_number": article.get('number', ''),
                    "title": article.get('title'),
                    "sub_items": json.dumps(sub_ids),
                    "sub_items_count": len(sub_ids),
                    "page_start": article.get('page_start'),
                    "page_end": article.get('page_end'),
                    "categories": json.dumps(processed.categories),
                    "edges_json": json.dumps({
                        "law": processed.law_id,
                        "internal": internal_refs,
                        "external": external_refs
                    })
                })

            # Schedules
            for schedule in processed.schedules:
                sched_id = schedule.get('id', '')
                if not sched_id:
                    # Generate ID if missing
                    sched_name = schedule.get('name', 'Unknown')
                    sched_id = f"sched:{processed.law_code.replace(' ', '').replace('.', '')}/{sched_name}"

                # Build schedule text from sections (not top-level 'text')
                # Schedules have 'sections' array with individual text entries
                schedule_text = schedule.get('text', '')
                if not schedule_text and 'sections' in schedule:
                    sections = schedule['sections']
                    section_texts = []
                    for sec in sections:
                        sec_num = sec.get('number', '')
                        sec_title = sec.get('title', '')
                        sec_text = sec.get('text', '')
                        if sec_text:
                            if sec_num:
                                section_texts.append(f"[{sec_num}] {sec_title + ': ' if sec_title else ''}{sec_text}")
                            else:
                                section_texts.append(sec_text)
                    schedule_text = "\n\n".join(section_texts)

                # Include AI description if available
                ai_desc = schedule.get('ai_description')
                if ai_desc:
                    schedule_text = f"{ai_desc}\n\n{schedule_text}"

                all_schedules.append({
                    "id": sched_id,
                    "type": "schedule",
                    "text": schedule_text,
                    "law_code": processed.law_code,
                    "law_name": processed.law_name,
                    "schedule_name": schedule.get('name', ''),
                    "title": schedule.get('title'),
                    "page_start": schedule.get('page_start'),
                    "page_end": schedule.get('page_end'),
                    "categories": json.dumps(processed.categories)
                })

            # Miscellaneous content (tariffs, forms, tables)
            for misc in processed.miscellaneous:
                misc_id = misc.get('id', '')
                misc_text = misc.get('text', '')
                if not misc_id or not misc_text:
                    continue

                all_miscellaneous.append({
                    "id": misc_id,
                    "type": "miscellaneous",
                    "text": misc_text,
                    "law_code": processed.law_code,
                    "law_name": processed.law_name,
                    "page": misc.get('page'),
                    "extraction_method": misc.get('extraction_method'),
                    "categories": json.dumps(processed.categories)
                })

            # Edges
            for i, edge in enumerate(processed.edges):
                edge_id = f"{edge.get('source_id', '')}--{edge.get('target_id', '')}--{i}"
                all_edges.append({
                    "id": edge_id,
                    "source_id": edge.get('source_id', ''),
                    "target_id": edge.get('target_id', ''),
                    "edge_type": edge.get('type', 'UNKNOWN'),
                    "source_type": "article",  # Most edges are from articles
                    "target_type": "article" if "art:" in edge.get('target_id', '') else "law",
                    "target_law": edge.get('target_law'),
                    "sub_target": edge.get('sub_target')
                })

            stats["successful"] += 1

        except Exception as e:
            logger.error(f"Error processing {json_file.name}: {e}")
            stats["failed"] += 1
            stats["failed_files"].append({"file": json_file.name, "reason": str(e)})

    logger.info(f"Loaded {len(all_law_summaries)} laws, {len(all_articles)} articles, {len(all_schedules)} schedules, {len(all_miscellaneous)} miscellaneous, {len(all_edges)} edges")

    # Embed law summaries
    if all_law_summaries:
        logger.info("Embedding law summaries...")
        summary_texts = [s["text"] for s in all_law_summaries]
        summary_embeddings = []
        for i in tqdm(range(0, len(summary_texts), batch_size), desc="Embedding summaries"):
            batch = summary_texts[i:i + batch_size]
            embeddings = embedder.embed_documents(batch)
            summary_embeddings.extend(embeddings)

        # Add vectors and store
        for summary, embedding in zip(all_law_summaries, summary_embeddings):
            summary["vector"] = embedding
        law_summaries_table.add(all_law_summaries)
        stats["total_laws"] = len(all_law_summaries)
        logger.info(f"Stored {len(all_law_summaries)} law summaries")

    # Embed articles
    if all_articles:
        logger.info("Embedding articles...")
        article_texts = [a["text"] for a in all_articles]
        article_embeddings = []
        for i in tqdm(range(0, len(article_texts), batch_size), desc="Embedding articles"):
            batch = article_texts[i:i + batch_size]
            embeddings = embedder.embed_documents(batch)
            article_embeddings.extend(embeddings)

        # Add vectors and store
        for article, embedding in zip(all_articles, article_embeddings):
            article["vector"] = embedding
        articles_table.add(all_articles)
        stats["total_articles"] = len(all_articles)
        logger.info(f"Stored {len(all_articles)} articles")

    # Embed schedules
    if all_schedules:
        logger.info("Embedding schedules...")
        schedule_texts = [s["text"] for s in all_schedules if s["text"]]
        valid_schedules = [s for s in all_schedules if s["text"]]

        if schedule_texts:
            schedule_embeddings = []
            for i in tqdm(range(0, len(schedule_texts), batch_size), desc="Embedding schedules"):
                batch = schedule_texts[i:i + batch_size]
                embeddings = embedder.embed_documents(batch)
                schedule_embeddings.extend(embeddings)

            for schedule, embedding in zip(valid_schedules, schedule_embeddings):
                schedule["vector"] = embedding
            schedules_table.add(valid_schedules)
            stats["total_schedules"] = len(valid_schedules)
            logger.info(f"Stored {len(valid_schedules)} schedules")

    # Embed miscellaneous content
    if all_miscellaneous:
        logger.info("Embedding miscellaneous content...")
        misc_texts = [m["text"] for m in all_miscellaneous if m["text"]]
        valid_misc = [m for m in all_miscellaneous if m["text"]]

        if misc_texts:
            misc_embeddings = []
            for i in tqdm(range(0, len(misc_texts), batch_size), desc="Embedding miscellaneous"):
                batch = misc_texts[i:i + batch_size]
                embeddings = embedder.embed_documents(batch)
                misc_embeddings.extend(embeddings)

            for misc, embedding in zip(valid_misc, misc_embeddings):
                misc["vector"] = embedding
            miscellaneous_table.add(valid_misc)
            stats["total_miscellaneous"] = len(valid_misc)
            logger.info(f"Stored {len(valid_misc)} miscellaneous items")

    # Store edges (no embedding needed)
    if all_edges:
        logger.info("Storing edges...")
        edges_table.add(all_edges)
        stats["total_edges"] = len(all_edges)
        logger.info(f"Stored {len(all_edges)} edges")

    # Save report
    report_path = extractions_path / "ingestion_report.json"
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Successful: {stats['successful']}/{stats['total_files']} files")
    print(f"Failed: {stats['failed']}/{stats['total_files']} files")
    print(f"\nDatabase contents:")
    print(f"  - Law summaries: {stats['total_laws']}")
    print(f"  - Articles: {stats['total_articles']}")
    print(f"  - Schedules: {stats['total_schedules']}")
    print(f"  - Miscellaneous: {stats['total_miscellaneous']}")
    print(f"  - Edges: {stats['total_edges']}")
    print(f"\nDatabase path: {db_path}")
    print(f"Report saved: {report_path}")

    if stats["failed_files"]:
        print("\nFailed files (first 10):")
        for f in stats["failed_files"][:10]:
            print(f"  - {f['file']}: {f['reason']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_json_extractions.py <extractions_directory>")
        print("Example: python scripts/ingest_json_extractions.py extractions/")
        print("\nOptions:")
        print("  --overwrite    Overwrite existing tables (default: append)")
        sys.exit(1)

    extractions_dir = sys.argv[1]
    overwrite = "--overwrite" in sys.argv

    ingest_extractions(extractions_dir, overwrite=overwrite)
