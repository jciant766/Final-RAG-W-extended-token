#!/usr/bin/env python3
"""
Export graph data to CSV files for Graphistry visualization.

Creates two CSVs:
1. nodes.csv - Laws and articles with meaningful metadata
2. edges.csv - Cross-references between articles/laws

For Graphistry:
- Upload nodes.csv and edges.csv
- Map node ID, label, category for coloring
- Map edge source, target, type
"""

import sys
from pathlib import Path
import json
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import lancedb


def export_for_graphistry(
    db_path: str = "./lancedb_graphrag",
    output_dir: str = "./graphistry_export",
    mode: str = "law_level"  # "law_level" or "article_level"
):
    """
    Export graph data for Graphistry visualization.

    Args:
        db_path: Path to LanceDB database
        output_dir: Directory to save CSV files
        mode:
            - "law_level": Aggregate to show law-to-law references (cleaner)
            - "article_level": Show individual article references (detailed)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print(f"Connecting to database at {db_path}...")
    db = lancedb.connect(db_path)

    # Load all data
    print("Loading data...")
    laws_df = db.open_table("law_summaries").to_pandas()
    articles_df = db.open_table("articles").to_pandas()
    edges_df = db.open_table("edges").to_pandas()

    print(f"  Laws: {len(laws_df)}")
    print(f"  Articles: {len(articles_df)}")
    print(f"  Edges: {len(edges_df)}")

    if mode == "law_level":
        export_law_level(laws_df, edges_df, output_path)
    else:
        export_article_level(laws_df, articles_df, edges_df, output_path)


def normalize_law_code(code):
    """Normalize law code to match database format (with spaces)."""
    if not code:
        return code
    # Convert "Cap.1" to "Cap. 1", "S.L.65.11" to "S.L. 65.11"
    import re
    # Add space after Cap., S.L., etc. if missing
    code = re.sub(r'(Cap\.)(\d)', r'\1 \2', code)
    code = re.sub(r'(S\.L\.)(\d)', r'\1 \2', code)
    code = re.sub(r'(L\.N\.)(\d)', r'\1 \2', code)
    return code


def export_law_level(laws_df, edges_df, output_path):
    """
    Export law-level graph showing which laws reference each other.
    Much cleaner visualization - shows the "big picture" of legal interconnections.
    """
    print("\n=== Exporting Law-Level Graph ===")

    # Build law lookup (with both normalized and original keys)
    law_info = {}
    for _, law in laws_df.iterrows():
        categories = json.loads(law.get('categories', '[]'))
        info = {
            'id': law['law_code'],
            'label': law['law_code'],
            'name': law['law_name'][:80],
            'category': categories[0] if categories else 'other',
            'total_articles': law.get('total_articles', 0),
            'type': 'law'
        }
        # Store with original key
        law_info[law['law_code']] = info
        # Also store with no-space version for matching edges
        no_space = law['law_code'].replace('. ', '.')
        if no_space != law['law_code']:
            law_info[no_space] = info

    # Aggregate edges to law-level
    # Extract law codes from article IDs
    def get_law_code(article_id):
        if article_id.startswith('art:'):
            # art:Cap.1/3 -> Cap.1
            parts = article_id.replace('art:', '').split('/')
            return parts[0]
        elif article_id.startswith('law:'):
            return article_id.replace('law:', '')
        return article_id

    # Only keep EXTERNAL_REF edges (cross-law references)
    external_edges = edges_df[edges_df['edge_type'] == 'EXTERNAL_REF'].copy()

    # Convert to law-level
    external_edges['source_law'] = external_edges['source_id'].apply(get_law_code)
    external_edges['target_law_code'] = external_edges['target_id'].apply(get_law_code)

    # Aggregate: count references between each pair of laws
    law_edges = external_edges.groupby(['source_law', 'target_law_code']).size().reset_index(name='weight')

    # Remove self-references
    law_edges = law_edges[law_edges['source_law'] != law_edges['target_law_code']]

    print(f"  External references aggregated to {len(law_edges)} law-to-law edges")

    # Filter to only include known Maltese laws (Cap. or S.L.)
    # This removes noise from unresolved references like "ActIIof2001", EU directives, etc.
    def is_maltese_law(code):
        return (code.startswith('Cap.') or code.startswith('Cap ') or
                code.startswith('S.L.') or code.startswith('S.L ') or
                code.startswith('L.N.') or code.startswith('L.N '))

    law_edges_clean = law_edges[
        law_edges['source_law'].apply(is_maltese_law) &
        law_edges['target_law_code'].apply(is_maltese_law)
    ]

    print(f"  Filtered to {len(law_edges_clean)} edges between known Maltese laws")
    law_edges = law_edges_clean

    # Find the most connected laws (top N by total references in + out)
    all_refs = pd.concat([
        law_edges.groupby('source_law')['weight'].sum(),
        law_edges.groupby('target_law_code')['weight'].sum()
    ])
    total_refs = all_refs.groupby(all_refs.index).sum().sort_values(ascending=False)

    # Take top 100 most connected laws for cleaner visualization
    TOP_N = 100
    top_laws = set(total_refs.head(TOP_N).index)
    print(f"  Top {TOP_N} most connected laws selected")

    # Filter edges to only those between top laws
    law_edges = law_edges[
        law_edges['source_law'].isin(top_laws) &
        law_edges['target_law_code'].isin(top_laws)
    ]
    print(f"  Edges between top laws: {len(law_edges)}")

    # Get unique laws that have edges
    laws_with_edges = set(law_edges['source_law']) | set(law_edges['target_law_code'])
    print(f"  Laws with cross-references: {len(laws_with_edges)}")

    # Create nodes CSV
    nodes_data = []
    for law_code in laws_with_edges:
        if law_code in law_info:
            nodes_data.append(law_info[law_code])
        else:
            # Law not in our database (might be referenced but not ingested)
            nodes_data.append({
                'id': law_code,
                'label': law_code,
                'name': f'{law_code} (external)',
                'category': 'external',
                'total_articles': 0,
                'type': 'law'
            })

    nodes_df = pd.DataFrame(nodes_data)

    # Create edges CSV
    edges_data = []
    for _, edge in law_edges.iterrows():
        source_name = law_info.get(edge['source_law'], {}).get('name', edge['source_law'])
        target_name = law_info.get(edge['target_law_code'], {}).get('name', edge['target_law_code'])

        edges_data.append({
            'source': edge['source_law'],
            'target': edge['target_law_code'],
            'weight': edge['weight'],
            'source_name': source_name[:50],
            'target_name': target_name[:50],
            'edge_type': 'CROSS_REFERENCE'
        })

    edges_out_df = pd.DataFrame(edges_data)

    # Save CSVs
    nodes_file = output_path / "nodes_laws.csv"
    edges_file = output_path / "edges_laws.csv"

    nodes_df.to_csv(nodes_file, index=False)
    edges_out_df.to_csv(edges_file, index=False)

    print(f"\nSaved:")
    print(f"  {nodes_file} ({len(nodes_df)} nodes)")
    print(f"  {edges_file} ({len(edges_out_df)} edges)")

    # Stats
    print(f"\nTop 10 most referenced laws:")
    ref_counts = edges_out_df.groupby('target')['weight'].sum().sort_values(ascending=False)
    for law_code, count in ref_counts.head(10).items():
        name = law_info.get(law_code, {}).get('name', 'Unknown')[:40]
        print(f"  {law_code}: {count} references - {name}")

    print(f"\nTop 10 laws that reference others most:")
    src_counts = edges_out_df.groupby('source')['weight'].sum().sort_values(ascending=False)
    for law_code, count in src_counts.head(10).items():
        name = law_info.get(law_code, {}).get('name', 'Unknown')[:40]
        print(f"  {law_code}: {count} outgoing refs - {name}")


def export_article_level(laws_df, articles_df, edges_df, output_path):
    """
    Export article-level graph showing specific cross-references.
    More detailed but can be overwhelming for large datasets.
    """
    print("\n=== Exporting Article-Level Graph ===")

    # Build lookups
    law_info = {}
    for _, law in laws_df.iterrows():
        categories = json.loads(law.get('categories', '[]'))
        law_info[law['law_code']] = {
            'name': law['law_name'],
            'category': categories[0] if categories else 'other'
        }

    article_info = {}
    for _, art in articles_df.iterrows():
        article_info[art['id']] = {
            'law_code': art['law_code'],
            'article_number': art['article_number'],
            'title': art.get('title', '')[:50] if art.get('title') else ''
        }

    # Only external references for clarity
    external_edges = edges_df[edges_df['edge_type'] == 'EXTERNAL_REF'].copy()

    # Limit to manageable size (top connected articles)
    edge_counts = external_edges['source_id'].value_counts()
    top_sources = edge_counts.head(500).index.tolist()

    filtered_edges = external_edges[external_edges['source_id'].isin(top_sources)]
    print(f"  Filtered to {len(filtered_edges)} edges from top 500 source articles")

    # Collect all node IDs
    all_nodes = set(filtered_edges['source_id']) | set(filtered_edges['target_id'])

    # Create nodes
    nodes_data = []
    for node_id in all_nodes:
        if node_id.startswith('art:'):
            info = article_info.get(node_id, {})
            law_code = info.get('law_code', node_id.split('/')[0].replace('art:', ''))
            law = law_info.get(law_code, {})

            label = f"Art. {info.get('article_number', '?')}"
            if info.get('title'):
                label += f": {info['title'][:30]}"

            nodes_data.append({
                'id': node_id,
                'label': label,
                'law_code': law_code,
                'law_name': law.get('name', '')[:50],
                'category': law.get('category', 'other'),
                'article_number': info.get('article_number', ''),
                'article_title': info.get('title', ''),
                'type': 'article'
            })
        elif node_id.startswith('law:'):
            law_code = node_id.replace('law:', '')
            law = law_info.get(law_code, {})

            nodes_data.append({
                'id': node_id,
                'label': law_code,
                'law_code': law_code,
                'law_name': law.get('name', '')[:50],
                'category': law.get('category', 'other'),
                'article_number': '',
                'article_title': '',
                'type': 'law'
            })

    nodes_df = pd.DataFrame(nodes_data)

    # Create edges
    edges_data = []
    for _, edge in filtered_edges.iterrows():
        src_info = article_info.get(edge['source_id'], {})

        edges_data.append({
            'source': edge['source_id'],
            'target': edge['target_id'],
            'edge_type': edge['edge_type'],
            'source_law': src_info.get('law_code', ''),
            'target_law': edge.get('target_law', '')
        })

    edges_out_df = pd.DataFrame(edges_data)

    # Save
    nodes_file = output_path / "nodes_articles.csv"
    edges_file = output_path / "edges_articles.csv"

    nodes_df.to_csv(nodes_file, index=False)
    edges_out_df.to_csv(edges_file, index=False)

    print(f"\nSaved:")
    print(f"  {nodes_file} ({len(nodes_df)} nodes)")
    print(f"  {edges_file} ({len(edges_out_df)} edges)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export graph data for Graphistry")
    parser.add_argument("--db", default="./lancedb_graphrag", help="Database path")
    parser.add_argument("--output", default="./graphistry_export", help="Output directory")
    parser.add_argument("--mode", choices=["law_level", "article_level"], default="law_level",
                       help="Export mode: law_level (aggregated) or article_level (detailed)")

    args = parser.parse_args()

    export_for_graphistry(args.db, args.output, args.mode)

    print("\n" + "="*60)
    print("GRAPHISTRY INSTRUCTIONS:")
    print("="*60)
    print("1. Go to https://hub.graphistry.com")
    print("2. Upload the nodes CSV and edges CSV")
    print("3. Configure:")
    print("   - Source: 'source' column")
    print("   - Destination: 'target' column")
    print("   - Node ID: 'id' column")
    print("   - Node Label: 'label' column")
    print("   - Node Color: 'category' column")
    print("   - Edge Weight: 'weight' column (for law_level)")
    print("="*60)
