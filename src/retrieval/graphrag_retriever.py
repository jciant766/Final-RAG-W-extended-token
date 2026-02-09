"""
Graph RAG Retriever for Maltese Laws.

Combines vector search with graph traversal using cross-reference edges.
Supports multi-hop queries for legal reasoning (A -> B -> C).

3-Stage Hierarchical Retrieval Pipeline:
1. Query Classification → Identify relevant legal categories (fast LLM)
2. Category Pre-filtering → Filter laws by category (instant, no embeddings)
3. Semantic Search → Search summaries within filtered laws
4. Article Search → Search articles within relevant laws
5. Graph Expansion → Follow cross-references

Based on research validation:
- 20-70% better comprehensiveness with graph traversal
- 3x better precision on multi-hop queries
- Category-first filtering improves precision (arxiv:2510.21711)
- Critical for legal documents with complex cross-references
"""

import lancedb
from typing import List, Dict, Any, Optional, Set, Tuple, Union
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# FUNDAMENTAL LAWS PER CATEGORY
# =============================================================================
# These are the core "foundational" laws for each legal category that MUST
# always be included in searches, regardless of semantic similarity ranking.
#
# Problem this solves: Semantic search may rank foundational laws lower because
# their summaries are generic (e.g., Civil Code covers everything from contracts
# to prescription periods). By always including these, we ensure the most
# important laws are never missed.
#
# Example: "statute of limitations for medical malpractice" → Civil Code (Cap. 16)
# contains Article 2153 on prescription periods, but may rank #67 in semantic
# similarity because the law summary doesn't mention "malpractice" specifically.
# =============================================================================
FUNDAMENTAL_LAWS = {
    "civil_law": [
        "Cap. 16",   # Civil Code - THE foundational civil law (contracts, torts, prescription, etc.)
        "Cap. 12",   # Code of Organization and Civil Procedure
    ],
    "criminal_law": [
        "Cap. 9",    # Criminal Code - THE foundational criminal law
        "Cap. 101",  # Code of Police Laws
    ],
    "commercial_law": [
        "Cap. 13",   # Commercial Code
        "Cap. 386",  # Companies Act
    ],
    "company_law": [
        "Cap. 386",  # Companies Act - THE foundational company law
    ],
    "family_law": [
        "Cap. 16",   # Civil Code (contains marriage, divorce, inheritance)
    ],
    "property_law": [
        "Cap. 16",   # Civil Code (contains property rights, ownership)
        "Cap. 158",  # Land Registration Act
    ],
    "employment_law": [
        "Cap. 452",  # Employment and Industrial Relations Act
    ],
    "tax_law": [
        "Cap. 123",  # Income Tax Act
        "Cap. 406",  # VAT Act
    ],
    "constitutional_law": [
        "Cap. 1",    # Constitution of Malta
    ],
    "administrative_law": [
        "Cap. 12",   # Code of Organization and Civil Procedure
    ],
    "health_law": [
        "Cap. 31",   # Medical and Kindred Professions Ordinance
        "Cap. 465",  # Health Act
    ],
    "financial_services_law": [
        "Cap. 330",  # Financial Institutions Act
        "Cap. 403",  # Investment Services Act
    ],
    "consumer_protection_law": [
        "Cap. 378",  # Consumer Affairs Act
    ],
    "immigration_law": [
        "Cap. 217",  # Immigration Act
    ],
    "environmental_law": [
        "Cap. 549",  # Environment Protection Act
    ],
    "planning_and_development_law": [
        "Cap. 552",  # Development Planning Act
    ],
    "data_protection_and_privacy": [
        "Cap. 586",  # Data Protection Act
    ],
}


# Lazy import for query classifier to avoid circular imports
_query_classifier = None

def _get_query_classifier():
    """Lazy load the query classifier."""
    global _query_classifier
    if _query_classifier is None:
        try:
            from src.retrieval.query_classifier import QueryClassifier
            _query_classifier = QueryClassifier()
        except Exception as e:
            logger.warning(f"Could not load QueryClassifier: {e}")
            _query_classifier = None
    return _query_classifier


def _expand_query(query: str) -> Dict[str, Any]:
    """
    Expand query with legal term synonyms.

    This bridges the gap between common English and legal terminology.
    For example: "statute of limitations" → expanded with "prescription"
    """
    try:
        from src.retrieval.query_classifier import expand_query
        return expand_query(query)
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}")
        return {
            "original_query": query,
            "expanded_query": query,
            "expansions": [],
            "terms_added": []
        }


class GraphRAGRetriever:
    """
    Hybrid retriever combining:
    1. Vector search (semantic similarity)
    2. Graph traversal (cross-reference edges)
    3. Category filtering (pre-filtering for efficiency)

    Follows VECTOR_DB_SCHEMA.md and GRAPH_RAG_FORMAT.md specifications.
    """

    def __init__(
        self,
        db_path: str = "./lancedb_graphrag",
        embedder=None
    ):
        """
        Initialize the Graph RAG retriever.

        Args:
            db_path: Path to LanceDB database
            embedder: VoyageEmbeddings instance (or will create one)
        """
        self.db_path = db_path
        self.db = None
        self.tables = {}
        self.embedder = embedder

        self._connect()

    def _connect(self):
        """Connect to LanceDB and open tables."""
        if not Path(self.db_path).exists():
            raise ValueError(f"Database not found at {self.db_path}. Run ingestion first.")

        self.db = lancedb.connect(self.db_path)

        # Open tables
        table_names = self.db.table_names()
        required_tables = ["law_summaries", "articles", "edges"]

        for name in required_tables:
            if name in table_names:
                self.tables[name] = self.db.open_table(name)
            else:
                logger.warning(f"Table '{name}' not found in database")

        if "schedules" in table_names:
            self.tables["schedules"] = self.db.open_table("schedules")

        logger.info(f"Connected to GraphRAG database with tables: {list(self.tables.keys())}")

    def _get_embedder(self):
        """Lazy load embedder."""
        if self.embedder is None:
            from src.embeddings.voyage_embeddings import VoyageEmbeddings
            self.embedder = VoyageEmbeddings()
        return self.embedder

    def search(
        self,
        query: str,
        limit: int = 10,
        categories: Optional[List[str]] = None,
        law_filter: Optional[str] = None,
        expand_graph: bool = True,
        max_hops: int = 1,
        include_schedules: bool = True,
        use_hierarchical: bool = True,
        top_laws: int = 10,
        auto_classify: bool = True
    ) -> Dict[str, Any]:
        """
        Perform Graph RAG search with 3-stage hierarchical filtering.

        Full pipeline (when auto_classify=True and use_hierarchical=True):
        1. CLASSIFY: Query → LLM classifies into categories (tax_law, criminal_law, etc.)
        2. PRE-FILTER: Filter law_summaries BY CATEGORY (instant, no embeddings)
        3. SEMANTIC SEARCH: Search within category-filtered laws
        4. ARTICLE SEARCH: Search articles within relevant laws
        5. GRAPH EXPANSION: Follow cross-references

        Args:
            query: Search query
            limit: Number of primary results
            categories: Explicit category filter (bypasses auto-classification)
            law_filter: Filter by specific law code (e.g., "Cap. 16") - bypasses hierarchical
            expand_graph: Whether to expand results using cross-reference edges
            max_hops: Maximum hops for graph traversal (1 or 2 recommended)
            include_schedules: Whether to include schedule results
            use_hierarchical: If True, search laws first then filter articles (recommended)
            top_laws: Number of top laws to search when using hierarchical filtering
            auto_classify: If True, use LLM to classify query into categories first

        Returns:
            Dict with:
                - articles: List of matching articles
                - related_articles: Articles found via graph traversal
                - laws: Related law summaries
                - schedules: Matching schedules (if include_schedules=True)
                - graph_path: The traversal path taken
                - laws_searched: List of law codes that were searched (hierarchical mode)
                - classification: Category classification results (if auto_classify=True)
                - query_expansion: Terms added via synonym expansion (if any)
        """
        # ============================================================
        # STAGE 0: Query Expansion (legal terminology synonyms)
        # ============================================================
        # Expand common terms with legal synonyms BEFORE embedding
        # Example: "statute of limitations" → "statute of limitations (prescription, time-barred)"
        expansion_result = _expand_query(query)
        search_query = expansion_result["expanded_query"]

        if expansion_result.get("terms_added"):
            logger.info(f"Query expanded: {query} → {search_query}")

        embedder = self._get_embedder()
        query_embedding = embedder.embed_query(search_query)  # Use expanded query for embedding

        results = {
            "query": query,
            "articles": [],
            "related_articles": [],
            "laws": [],
            "schedules": [],
            "graph_path": [],
            "laws_searched": [],
            "classification": None,
            "categories_used": [],
            "query_expansion": expansion_result if expansion_result.get("terms_added") else None
        }

        # ============================================================
        # STAGE 1: Query Classification (if enabled and no explicit categories)
        # ============================================================
        effective_categories = categories
        if auto_classify and not categories and not law_filter:
            classifier = _get_query_classifier()
            if classifier:
                try:
                    classification = classifier.classify(query, max_categories=3)
                    results["classification"] = classification

                    if classification.get("categories"):
                        effective_categories = classification["categories"]
                        results["categories_used"] = effective_categories
                        logger.info(f"Query classified into: {effective_categories} "
                                  f"(confidence: {classification.get('confidence', {})})")
                except Exception as e:
                    logger.warning(f"Query classification failed: {e}")

        # ============================================================
        # STAGE 2: Category Pre-filtering + Law Summary Search
        # ============================================================
        law_results = []
        if "law_summaries" in self.tables:
            # Search law summaries WITH category pre-filter
            law_results = self._search_laws(
                query_embedding,
                categories=effective_categories,  # Pre-filtered by category!
                limit=top_laws
            )
            results["laws"] = law_results

        # ============================================================
        # STAGE 3: Determine which laws to search for articles
        # ============================================================
        laws_to_search = None
        if law_filter:
            # User explicitly specified a law - use it directly
            laws_to_search = [law_filter] if isinstance(law_filter, str) else law_filter
            results["laws_searched"] = laws_to_search
            logger.info(f"Using explicit law filter: {laws_to_search}")
        elif use_hierarchical and law_results:
            # Hierarchical mode: extract law codes from summary search results
            laws_to_search = [law["law_code"] for law in law_results]

            # ============================================================
            # STAGE 3a: Include PARENT CHAPTERS for subsidiary legislation
            # ============================================================
            # When S.L. 452.xx laws are found, Cap. 452 likely contains the
            # fundamental provisions. Always include parent chapters.
            parent_chapters = set()
            for law_code in laws_to_search:
                if law_code.startswith("S.L. "):
                    # Extract parent chapter number: S.L. 452.81 → 452
                    parts = law_code.replace("S.L. ", "").split(".")
                    if parts:
                        parent = f"Cap. {parts[0]}"
                        if parent not in laws_to_search:
                            parent_chapters.add(parent)

            if parent_chapters:
                laws_to_search = laws_to_search + list(parent_chapters)
                results["parent_laws_added"] = list(parent_chapters)
                logger.info(f"Added {len(parent_chapters)} parent chapters: {parent_chapters}")

            # ============================================================
            # STAGE 3b: Inject FUNDAMENTAL LAWS for detected categories
            # ============================================================
            # Always include foundational laws for the detected categories,
            # even if they didn't rank highly in semantic search.
            # This ensures we never miss core laws like Civil Code for civil matters.
            if effective_categories:
                fundamental_to_add = set()
                for category in effective_categories:
                    if category in FUNDAMENTAL_LAWS:
                        for law_code in FUNDAMENTAL_LAWS[category]:
                            if law_code not in laws_to_search:
                                fundamental_to_add.add(law_code)

                if fundamental_to_add:
                    # Add fundamental laws at the END of the list
                    # (semantic results first, then fundamental laws as safety net)
                    laws_to_search = laws_to_search + list(fundamental_to_add)
                    results["fundamental_laws_added"] = list(fundamental_to_add)
                    logger.info(f"Injected {len(fundamental_to_add)} fundamental laws: {fundamental_to_add}")

            results["laws_searched"] = laws_to_search
            logger.info(f"Hierarchical filtering: searching {len(laws_to_search)} laws")
            logger.info(f"Law codes: {laws_to_search[:5]}")

        # ============================================================
        # STAGE 4: Article Search (within filtered laws)
        # ============================================================
        if "articles" in self.tables:
            # When using hierarchical filtering (law_filter is set), skip category filter
            # since the laws are already category-filtered. This avoids double-filtering.
            article_categories = None if laws_to_search else effective_categories

            article_results = self._search_articles(
                query_embedding,
                categories=article_categories,
                law_filter=laws_to_search,
                limit=limit
            )

            # FALLBACK: If hierarchical search returns 0 results, search with category only
            # This handles cases where the top law summaries have no articles (e.g., S.L. regulations)
            if not article_results and laws_to_search and effective_categories:
                logger.warning(f"Hierarchical search returned 0 articles, falling back to category search")
                article_results = self._search_articles(
                    query_embedding,
                    categories=effective_categories,
                    law_filter=None,  # Search all laws in category
                    limit=limit
                )
                results["fallback_used"] = True

            results["articles"] = article_results

        # ============================================================
        # STAGE 5: Graph Expansion (follow cross-references)
        # ============================================================
        if expand_graph and results["articles"] and "edges" in self.tables:
            primary_ids = [a["id"] for a in results["articles"]]
            related, paths = self._expand_graph(
                primary_ids,
                max_hops=max_hops,
                limit=limit
            )
            results["related_articles"] = related
            results["graph_path"] = paths

        # ============================================================
        # STAGE 6: Schedule Search (within filtered laws)
        # ============================================================
        if include_schedules and "schedules" in self.tables:
            # Same logic: skip category filter when using hierarchical filtering
            schedule_categories = None if laws_to_search else effective_categories

            schedule_results = self._search_schedules(
                query_embedding,
                categories=schedule_categories,
                law_filter=laws_to_search,
                limit=5
            )
            results["schedules"] = schedule_results

        return results

    def _search_laws(
        self,
        query_embedding: List[float],
        categories: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Search law summaries."""
        table = self.tables["law_summaries"]
        search = table.search(query_embedding)

        # Apply category filter
        if categories:
            # LanceDB filter for JSON array contains
            category_filters = [f"categories LIKE '%{cat}%'" for cat in categories]
            search = search.where(" OR ".join(category_filters))

        results = search.limit(limit).to_pandas()
        # Drop vector column to avoid numpy array serialization issues
        if 'vector' in results.columns:
            results = results.drop(columns=['vector'])
        records = results.to_dict('records')

        # Parse JSON fields
        for record in records:
            record['categories'] = json.loads(record.get('categories', '[]'))
            record['key_topics'] = json.loads(record.get('key_topics', '[]'))
            if 'edges_json' in record:
                record['edges'] = json.loads(record.get('edges_json', '{}'))
                del record['edges_json']

        return records

    def _search_articles(
        self,
        query_embedding: List[float],
        categories: Optional[List[str]] = None,
        law_filter: Optional[Union[str, List[str]]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search articles with filtering.

        Args:
            query_embedding: Query vector
            categories: Filter by legal categories
            law_filter: Filter by law code(s) - can be single string or list
                       e.g., "Cap. 9" or ["Cap. 9", "Cap. 386", "S.L. 441.04"]
            limit: Number of results
        """
        table = self.tables["articles"]
        search = table.search(query_embedding)

        # Build filters
        filters = []

        # Handle law_filter - can be single string or list of law codes
        if law_filter:
            if isinstance(law_filter, str):
                filters.append(f"law_code = '{law_filter}'")
            elif isinstance(law_filter, list) and len(law_filter) > 0:
                # Multiple law codes - use OR condition
                law_conditions = [f"law_code = '{code}'" for code in law_filter]
                filters.append(f"({' OR '.join(law_conditions)})")

        if categories:
            category_filters = [f"categories LIKE '%{cat}%'" for cat in categories]
            filters.append(f"({' OR '.join(category_filters)})")

        if filters:
            filter_str = " AND ".join(filters)
            logger.info(f"Article search filter: {filter_str[:200]}")  # Log first 200 chars
            search = search.where(filter_str)

        results = search.limit(limit).to_pandas()
        # Drop vector column to avoid numpy array serialization issues
        if 'vector' in results.columns:
            results = results.drop(columns=['vector'])
        records = results.to_dict('records')
        logger.info(f"Article search returned {len(records)} results")

        # Parse JSON fields
        for record in records:
            record['categories'] = json.loads(record.get('categories', '[]'))
            record['sub_items'] = json.loads(record.get('sub_items', '[]'))
            if 'edges_json' in record:
                record['edges'] = json.loads(record.get('edges_json', '{}'))
                del record['edges_json']

        return records

    def _search_schedules(
        self,
        query_embedding: List[float],
        categories: Optional[List[str]] = None,
        law_filter: Optional[Union[str, List[str]]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search schedules with filtering.

        Args:
            query_embedding: Query vector
            categories: Filter by legal categories
            law_filter: Filter by law code(s) - can be single string or list
            limit: Number of results
        """
        if "schedules" not in self.tables:
            return []

        table = self.tables["schedules"]
        search = table.search(query_embedding)

        filters = []

        # Handle law_filter - can be single string or list of law codes
        if law_filter:
            if isinstance(law_filter, str):
                filters.append(f"law_code = '{law_filter}'")
            elif isinstance(law_filter, list) and len(law_filter) > 0:
                law_conditions = [f"law_code = '{code}'" for code in law_filter]
                filters.append(f"({' OR '.join(law_conditions)})")

        if categories:
            category_filters = [f"categories LIKE '%{cat}%'" for cat in categories]
            filters.append(f"({' OR '.join(category_filters)})")

        if filters:
            search = search.where(" AND ".join(filters))

        results = search.limit(limit).to_pandas()
        # Drop vector column to avoid numpy array serialization issues
        if 'vector' in results.columns:
            results = results.drop(columns=['vector'])
        records = results.to_dict('records')

        for record in records:
            record['categories'] = json.loads(record.get('categories', '[]'))

        return records

    def _expand_graph(
        self,
        article_ids: List[str],
        max_hops: int = 1,
        limit: int = 10
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Expand search results using cross-reference edges.

        This is the key Graph RAG feature - finding related articles
        through the cross-reference graph.
        """
        edges_table = self.tables["edges"]
        articles_table = self.tables["articles"]

        visited: Set[str] = set(article_ids)
        related_ids: Set[str] = set()
        paths = []

        current_ids = article_ids

        for hop in range(max_hops):
            if not current_ids:
                break

            # Find edges from current articles
            id_filters = [f"source_id = '{aid}'" for aid in current_ids]
            filter_str = " OR ".join(id_filters)

            try:
                edges_df = edges_table.search().where(filter_str).limit(100).to_pandas()

                new_targets = []
                for _, edge in edges_df.iterrows():
                    target_id = edge['target_id']
                    if target_id not in visited and target_id.startswith('art:'):
                        related_ids.add(target_id)
                        new_targets.append(target_id)
                        visited.add(target_id)

                        paths.append({
                            "from": edge['source_id'],
                            "to": target_id,
                            "type": edge['edge_type'],
                            "hop": hop + 1
                        })

                current_ids = new_targets[:20]  # Limit expansion

            except Exception as e:
                logger.warning(f"Error during graph expansion: {e}")
                break

        # Fetch article details for related IDs
        related_articles = []
        if related_ids:
            for rel_id in list(related_ids)[:limit]:
                try:
                    result = articles_table.search().where(f"id = '{rel_id}'").limit(1).to_pandas()
                    if len(result) > 0:
                        # Drop vector column to avoid numpy array serialization issues
                        if 'vector' in result.columns:
                            result = result.drop(columns=['vector'])
                        record = result.iloc[0].to_dict()
                        record['categories'] = json.loads(record.get('categories', '[]'))
                        record['sub_items'] = json.loads(record.get('sub_items', '[]'))
                        if 'edges_json' in record:
                            record['edges'] = json.loads(record.get('edges_json', '{}'))
                            del record['edges_json']
                        record['found_via'] = 'graph_traversal'
                        related_articles.append(record)
                except Exception as e:
                    logger.warning(f"Error fetching related article {rel_id}: {e}")

        return related_articles, paths

    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """Get a specific article by its Graph RAG ID."""
        if "articles" not in self.tables:
            return None

        try:
            result = self.tables["articles"].search().where(f"id = '{article_id}'").limit(1).to_pandas()
            if len(result) == 0:
                return None

            # Drop vector column to avoid numpy array serialization issues
            if 'vector' in result.columns:
                result = result.drop(columns=['vector'])
            record = result.iloc[0].to_dict()
            record['categories'] = json.loads(record.get('categories', '[]'))
            record['sub_items'] = json.loads(record.get('sub_items', '[]'))
            if 'edges_json' in record:
                record['edges'] = json.loads(record.get('edges_json', '{}'))
                del record['edges_json']
            return record
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {e}")
            return None

    def get_related_articles(
        self,
        article_id: str,
        edge_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get all articles related to a given article via edges.

        Args:
            article_id: The source article ID (e.g., "art:Cap.1/3")
            edge_types: Filter by edge types (e.g., ["INTERNAL_REF", "EXTERNAL_REF"])

        Returns:
            List of related articles with edge information
        """
        if "edges" not in self.tables:
            return []

        try:
            # Find outgoing edges
            filter_str = f"source_id = '{article_id}'"
            edges_df = self.tables["edges"].search().where(filter_str).limit(50).to_pandas()

            related = []
            for _, edge in edges_df.iterrows():
                if edge_types and edge['edge_type'] not in edge_types:
                    continue

                target_id = edge['target_id']
                if target_id.startswith('art:'):
                    article = self.get_article_by_id(target_id)
                    if article:
                        article['edge_type'] = edge['edge_type']
                        article['edge_from'] = article_id
                        related.append(article)

            return related
        except Exception as e:
            logger.error(f"Error getting related articles: {e}")
            return []

    def count(self) -> Dict[str, int]:
        """Get counts for all tables."""
        counts = {}
        for name, table in self.tables.items():
            try:
                counts[name] = table.count_rows()
            except Exception:
                counts[name] = 0
        return counts


def build_rag_context(search_results: Dict[str, Any], max_articles: int = 5) -> str:
    """
    Build context string for LLM from search results.

    Args:
        search_results: Output from GraphRAGRetriever.search()
        max_articles: Maximum number of articles to include

    Returns:
        Formatted context string for the LLM
    """
    parts = []

    # Show query classification (if available)
    if search_results.get("classification"):
        classification = search_results["classification"]
        if classification.get("categories"):
            parts.append(f"## Query Classification")
            parts.append(f"Legal domains: {', '.join(classification['categories'])}")
            parts.append(f"Reasoning: {classification.get('reasoning', 'N/A')}")
            parts.append("")

    # Show which laws were searched (hierarchical filtering transparency)
    if search_results.get("laws_searched"):
        parts.append(f"## Search Scope: {len(search_results['laws_searched'])} Relevant Laws")
        parts.append(f"Laws searched: {', '.join(search_results['laws_searched'][:5])}")
        if len(search_results['laws_searched']) > 5:
            parts.append(f"... and {len(search_results['laws_searched']) - 5} more")
        parts.append("")

    # Add law context (summaries with key topics)
    if search_results.get("laws"):
        parts.append("## Relevant Laws\n")
        for law in search_results["laws"][:3]:
            parts.append(f"**{law['law_code']}**: {law['law_name']}")
            parts.append(f"{law['text']}")
            # Include key topics if available (very useful for context!)
            key_topics = law.get('key_topics', [])
            if key_topics and isinstance(key_topics, list) and len(key_topics) > 0:
                parts.append(f"Key topics: {', '.join(key_topics[:5])}")
            parts.append("")

    # Add primary articles
    if search_results.get("articles"):
        parts.append("\n## Primary Articles\n")
        for article in search_results["articles"][:max_articles]:
            citation = f"{article['law_code']}, Article {article['article_number']}"
            if article.get('title'):
                citation += f" - {article['title']}"
            parts.append(f"### {citation}\n")
            parts.append(article['text'])
            parts.append("")

    # Add related articles (from graph traversal)
    if search_results.get("related_articles"):
        parts.append("\n## Related Articles (Cross-References)\n")
        for article in search_results["related_articles"][:3]:
            citation = f"{article['law_code']}, Article {article['article_number']}"
            parts.append(f"### {citation} (via cross-reference)\n")
            parts.append(article['text'])
            parts.append("")

    # Add schedules
    if search_results.get("schedules"):
        parts.append("\n## Relevant Schedules\n")
        for schedule in search_results["schedules"][:2]:
            parts.append(f"### {schedule['law_code']} - {schedule['schedule_name']}")
            parts.append(schedule['text'])
            parts.append("")

    return "\n".join(parts)
