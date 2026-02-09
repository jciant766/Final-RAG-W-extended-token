"""
Enhanced legal reference graph supporting all reference types.

Handles:
- Chapter → Chapter references
- Chapter → Article references
- Internal article → article references
- S.L. references
- Legal Notice tracking
- Act references
- Amendment history
"""

import networkx as nx
import pickle
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EdgeType(Enum):
    """Types of relationships between legal provisions."""
    REFERENCES = "references"  # Standard cross-reference
    AMENDS = "amends"  # One law amends another
    REPEALS = "repeals"  # One law repeals another
    DEFINES = "defines"  # One law defines terms in another
    IMPLEMENTS = "implements"  # One law implements another (S.L. → Cap.)
    INTERNAL = "internal"  # Same chapter reference


class EnhancedLegalReferenceGraph:
    """
    Comprehensive graph of legal relationships.

    Nodes: (type, chapter, article) tuples
    - ("cap", "490", "5") - Chapter 490, Article 5
    - ("sl", "653.05", "reg3") - S.L. 653.05, Regulation 3
    - ("cap", "386", "*") - Entire Chapter 386

    Edges: Typed relationships with metadata
    """

    def __init__(self, graph_path: str = "./lancedb_data/reference_graph.pkl"):
        self.graph_path = Path(graph_path)
        self.graph = nx.MultiDiGraph()  # Multi allows multiple edge types

        # Metadata stores
        self.chapter_names = {}  # chapter_num → name
        self.sl_names = {}  # sl_num → name
        self.legal_notices = {}  # chapter → [list of L.N.]
        self.act_references = {}  # chapter → [list of Act refs]

        # Load if exists
        if self.graph_path.exists():
            self.load()

    # ========================================
    # ADDING REFERENCES
    # ========================================

    def add_reference(
        self,
        source_type: str,  # "cap" or "sl"
        source_chapter: str,
        source_article: Optional[str],
        target_type: str,
        target_chapter: str,
        target_article: Optional[str],
        edge_type: EdgeType = EdgeType.REFERENCES,
        context: str = "",
        metadata: Optional[Dict] = None
    ):
        """Add a reference edge to the graph."""

        # Create node identifiers
        source_node = (source_type, source_chapter, source_article or "*")
        target_node = (target_type, target_chapter, target_article or "*")

        # Add nodes
        if source_node not in self.graph:
            self.graph.add_node(
                source_node,
                type=source_type,
                chapter=source_chapter,
                article=source_article
            )

        if target_node not in self.graph:
            self.graph.add_node(
                target_node,
                type=target_type,
                chapter=target_chapter,
                article=target_article
            )

        # Add edge with metadata
        edge_attrs = {
            'edge_type': edge_type.value,
            'context': context,
            **(metadata or {})
        }

        self.graph.add_edge(source_node, target_node, **edge_attrs)

        logger.debug(f"Added reference: {source_node} --[{edge_type.value}]--> {target_node}")

    def add_internal_reference(
        self,
        chapter_type: str,
        chapter: str,
        source_article: str,
        target_article: str,
        context: str = ""
    ):
        """Add internal reference (within same chapter)."""
        self.add_reference(
            source_type=chapter_type,
            source_chapter=chapter,
            source_article=source_article,
            target_type=chapter_type,
            target_chapter=chapter,
            target_article=target_article,
            edge_type=EdgeType.INTERNAL,
            context=context
        )

    def add_legal_notice(self, chapter: str, legal_notice: str):
        """Track Legal Notice reference (amendment history)."""
        if chapter not in self.legal_notices:
            self.legal_notices[chapter] = []
        if legal_notice not in self.legal_notices[chapter]:
            self.legal_notices[chapter].append(legal_notice)

    def add_act_reference(self, chapter: str, act_reference: str):
        """Track Act reference."""
        if chapter not in self.act_references:
            self.act_references[chapter] = []
        if act_reference not in self.act_references[chapter]:
            self.act_references[chapter].append(act_reference)

    def add_chapter_name(self, chapter_number: str, chapter_title: str):
        """Store chapter name mapping."""
        self.chapter_names[chapter_number] = chapter_title

    def add_sl_name(self, sl_number: str, sl_title: str):
        """Store S.L. name mapping."""
        self.sl_names[sl_number] = sl_title

    # ========================================
    # QUERYING
    # ========================================

    def get_referenced_provisions(
        self,
        chapter_type: str,
        chapter: str,
        article: Optional[str],
        max_hops: int = 2,
        include_internal: bool = True,
        edge_types: Optional[List[EdgeType]] = None
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Get all provisions referenced by this provision.

        Args:
            chapter_type: "cap" or "sl"
            chapter: Chapter number
            article: Article/regulation number (None for whole chapter)
            max_hops: Maximum traversal depth
            include_internal: Include internal references
            edge_types: Filter by edge types

        Returns:
            List of (type, chapter, article) tuples
        """
        source_node = (chapter_type, chapter, article or "*")

        if source_node not in self.graph:
            return []

        referenced = set()

        # BFS traversal
        visited = {source_node}
        current_level = {source_node}

        for hop in range(1, max_hops + 1):
            next_level = set()

            for node in current_level:
                # Get all outgoing edges
                for _, target, edge_data in self.graph.out_edges(node, data=True):
                    # Filter by edge type if specified
                    if edge_types:
                        if edge_data.get('edge_type') not in [et.value for et in edge_types]:
                            continue

                    # Filter internal references if not wanted
                    if not include_internal and edge_data.get('edge_type') == EdgeType.INTERNAL.value:
                        continue

                    if target not in visited:
                        referenced.add(target)
                        next_level.add(target)
                        visited.add(target)

            current_level = next_level

        # Remove source and convert to list
        referenced.discard(source_node)
        return list(referenced)

    def get_referencing_provisions(
        self,
        chapter_type: str,
        chapter: str,
        article: Optional[str],
        max_hops: int = 1
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Get all provisions that reference this provision (reverse search).

        Args:
            chapter_type: "cap" or "sl"
            chapter: Chapter number
            article: Article number
            max_hops: Maximum traversal depth

        Returns:
            List of (type, chapter, article) tuples
        """
        target_node = (chapter_type, chapter, article or "*")

        if target_node not in self.graph:
            return []

        referencing = set()
        visited = {target_node}
        current_level = {target_node}

        for hop in range(1, max_hops + 1):
            next_level = set()

            for node in current_level:
                # Get all incoming edges
                for source, _ in self.graph.in_edges(node):
                    if source not in visited:
                        referencing.add(source)
                        next_level.add(source)
                        visited.add(source)

            current_level = next_level

        referencing.discard(target_node)
        return list(referencing)

    def get_chapter_references(
        self,
        chapter_type: str,
        chapter: str,
        outgoing: bool = True
    ) -> List[str]:
        """
        Get all chapters referenced by or referencing this chapter.

        Args:
            chapter_type: "cap" or "sl"
            chapter: Chapter number
            outgoing: If True, get outgoing refs; if False, get incoming

        Returns:
            List of chapter numbers
        """
        chapters = set()

        # Find all nodes for this chapter
        chapter_nodes = [
            node for node in self.graph.nodes()
            if node[0] == chapter_type and node[1] == chapter
        ]

        for node in chapter_nodes:
            if outgoing:
                neighbors = [target for _, target in self.graph.out_edges(node)]
            else:
                neighbors = [source for source, _ in self.graph.in_edges(node)]

            for neighbor in neighbors:
                neighbor_type, neighbor_chapter, _ = neighbor
                if neighbor_chapter != chapter:  # Exclude self
                    chapters.add((neighbor_type, neighbor_chapter))

        return list(chapters)

    def get_internal_references(
        self,
        chapter_type: str,
        chapter: str,
        article: str
    ) -> List[str]:
        """
        Get all articles referenced within the same chapter.

        Returns:
            List of article identifiers
        """
        source_node = (chapter_type, chapter, article)

        if source_node not in self.graph:
            return []

        internal_refs = []

        for _, target, edge_data in self.graph.out_edges(source_node, data=True):
            if edge_data.get('edge_type') == EdgeType.INTERNAL.value:
                _, _, target_article = target
                if target_article and target_article != "*":
                    internal_refs.append(target_article)

        return internal_refs

    def get_legal_notices(self, chapter: str) -> List[str]:
        """Get Legal Notices that amended this chapter."""
        return self.legal_notices.get(chapter, [])

    def get_act_references_for_chapter(self, chapter: str) -> List[str]:
        """Get Act references for a chapter."""
        return self.act_references.get(chapter, [])

    def get_reference_context(
        self,
        source_type: str,
        source_chapter: str,
        source_article: Optional[str],
        target_type: str,
        target_chapter: str,
        target_article: Optional[str]
    ) -> Optional[str]:
        """Get context text for a specific reference."""
        source_node = (source_type, source_chapter, source_article or "*")
        target_node = (target_type, target_chapter, target_article or "*")

        if self.graph.has_edge(source_node, target_node):
            # Get first edge (there may be multiple)
            edge_data = list(self.graph[source_node][target_node].values())[0]
            return edge_data.get('context')
        return None

    # ========================================
    # GRAPH ANALYTICS
    # ========================================

    def get_most_referenced_provisions(self, n: int = 10) -> List[Tuple[Tuple, int]]:
        """Get provisions with most incoming references."""
        in_degrees = self.graph.in_degree()
        sorted_nodes = sorted(in_degrees, key=lambda x: x[1], reverse=True)
        return sorted_nodes[:n]

    def get_most_citing_provisions(self, n: int = 10) -> List[Tuple[Tuple, int]]:
        """Get provisions with most outgoing references."""
        out_degrees = self.graph.out_degree()
        sorted_nodes = sorted(out_degrees, key=lambda x: x[1], reverse=True)
        return sorted_nodes[:n]

    def get_connected_components(self) -> List[Set]:
        """Get connected components (clusters of related laws)."""
        # Convert to undirected for component analysis
        undirected = self.graph.to_undirected()
        components = list(nx.connected_components(undirected))
        return components

    def get_shortest_path(
        self,
        source_type: str,
        source_chapter: str,
        source_article: Optional[str],
        target_type: str,
        target_chapter: str,
        target_article: Optional[str]
    ) -> Optional[List[Tuple]]:
        """Find shortest path between two provisions."""
        source_node = (source_type, source_chapter, source_article or "*")
        target_node = (target_type, target_chapter, target_article or "*")

        try:
            path = nx.shortest_path(self.graph, source_node, target_node)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_stats(self) -> Dict:
        """Get comprehensive graph statistics."""
        cap_nodes = [n for n in self.graph.nodes() if n[0] == "cap"]
        sl_nodes = [n for n in self.graph.nodes() if n[0] == "sl"]

        # Count edge types
        edge_type_counts = {}
        for _, _, data in self.graph.edges(data=True):
            edge_type = data.get('edge_type', 'unknown')
            edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1

        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'cap_provisions': len(cap_nodes),
            'sl_provisions': len(sl_nodes),
            'total_chapters': len(set(n[1] for n in cap_nodes)),
            'total_sls': len(set(n[1] for n in sl_nodes)),
            'edge_type_breakdown': edge_type_counts,
            'avg_references_per_provision': (
                self.graph.number_of_edges() / self.graph.number_of_nodes()
                if self.graph.number_of_nodes() > 0 else 0
            ),
            'most_referenced': self.get_most_referenced_provisions(5),
            'most_citing': self.get_most_citing_provisions(5),
            'total_legal_notices': sum(len(lns) for lns in self.legal_notices.values()),
            'total_act_references': sum(len(acts) for acts in self.act_references.values())
        }

    # ========================================
    # PERSISTENCE
    # ========================================

    def save(self):
        """Save graph to disk."""
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'graph': self.graph,
            'chapter_names': self.chapter_names,
            'sl_names': self.sl_names,
            'legal_notices': self.legal_notices,
            'act_references': self.act_references
        }

        with open(self.graph_path, 'wb') as f:
            pickle.dump(data, f)

        stats = self.get_stats()
        logger.info(
            f"Saved reference graph: {stats['total_nodes']} nodes, "
            f"{stats['total_edges']} edges ({stats['total_chapters']} chapters, "
            f"{stats['total_sls']} S.L.)"
        )

    def load(self):
        """Load graph from disk."""
        try:
            with open(self.graph_path, 'rb') as f:
                data = pickle.load(f)

            self.graph = data.get('graph', nx.MultiDiGraph())
            self.chapter_names = data.get('chapter_names', {})
            self.sl_names = data.get('sl_names', {})
            self.legal_notices = data.get('legal_notices', {})
            self.act_references = data.get('act_references', {})

            stats = self.get_stats()
            logger.info(
                f"Loaded reference graph: {stats['total_nodes']} nodes, "
                f"{stats['total_edges']} edges"
            )

        except Exception as e:
            logger.warning(f"Could not load reference graph: {e}")
            self.graph = nx.MultiDiGraph()

    def export_to_graphml(self, output_path: str):
        """Export to GraphML format for visualization tools."""
        # Convert to simple graph (no multi-edges) for compatibility
        simple_graph = nx.DiGraph()

        for u, v, data in self.graph.edges(data=True):
            # Create node labels
            u_label = f"{u[0].upper()}.{u[1]}.{u[2] if u[2] != '*' else 'ALL'}"
            v_label = f"{v[0].upper()}.{v[1]}.{v[2] if v[2] != '*' else 'ALL'}"

            simple_graph.add_node(u_label, **{'type': u[0], 'chapter': u[1], 'article': u[2]})
            simple_graph.add_node(v_label, **{'type': v[0], 'chapter': v[1], 'article': v[2]})
            simple_graph.add_edge(u_label, v_label, **data)

        nx.write_graphml(simple_graph, output_path)
        logger.info(f"Exported graph to GraphML: {output_path}")
