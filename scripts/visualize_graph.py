#!/usr/bin/env python3
"""
Visualize the Graph RAG structure as an interactive HTML graph.

Creates an interactive network visualization showing:
- Law nodes (large, colored by category)
- Article nodes (medium)
- Edges (cross-references between articles/laws)

Run: python scripts/visualize_graph.py
Opens: graph_visualization.html in browser
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pyvis.network import Network
except ImportError:
    print("Installing pyvis for visualization...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyvis"])
    from pyvis.network import Network

import lancedb


def visualize_graph(
    db_path: str = "./lancedb_graphrag",
    output_file: str = "graph_visualization.html",
    max_laws: int = 500,
    max_edges: int = 10000
):
    """Create interactive graph visualization."""

    print(f"Connecting to database at {db_path}...")
    db = lancedb.connect(db_path)

    # Create network
    net = Network(
        height="900px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True
    )

    # Physics settings for better layout - keep nodes centered
    net.set_options("""
    {
        "nodes": {
            "font": {"size": 14, "color": "white"}
        },
        "edges": {
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
            "smooth": {"type": "continuous"}
        },
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -3000,
                "centralGravity": 0.5,
                "springLength": 150,
                "springConstant": 0.04,
                "damping": 0.3
            },
            "maxVelocity": 30,
            "solver": "barnesHut",
            "stabilization": {"iterations": 200, "fit": true}
        },
        "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true,
            "zoomView": true
        }
    }
    """)

    # Category colors
    category_colors = {
        "criminal_law": "#e74c3c",
        "civil_law": "#3498db",
        "commercial_law": "#2ecc71",
        "administrative_law": "#9b59b6",
        "constitutional_law": "#f39c12",
        "eu_law": "#1abc9c",
        "tax_law": "#e67e22",
        "health_law": "#fd79a8",
        "default": "#95a5a6"
    }

    added_nodes = set()

    # Add law summary nodes
    if "law_summaries" in db.table_names():
        print("Loading law summaries...")
        laws_table = db.open_table("law_summaries")
        laws_df = laws_table.to_pandas()

        for _, law in laws_df.head(max_laws).iterrows():
            law_id = law['id']
            categories = json.loads(law.get('categories', '[]'))
            color = category_colors.get(categories[0] if categories else 'default', category_colors['default'])

            net.add_node(
                law_id,
                label=law['law_code'],
                title=f"{law['law_code']}: {law['law_name']}\n\nCategories: {', '.join(categories)}\nArticles: {law.get('total_articles', 0)}",
                color=color,
                size=30,
                shape="dot"
            )
            added_nodes.add(law_id)

        print(f"Added {len(added_nodes)} law nodes")

    # Add edges
    if "edges" in db.table_names():
        print("Loading edges...")
        edges_table = db.open_table("edges")
        edges_df = edges_table.to_pandas()

        edge_count = 0
        internal_count = 0
        external_count = 0

        for _, edge in edges_df.head(max_edges).iterrows():
            source = edge['source_id']
            target = edge['target_id']
            edge_type = edge['edge_type']

            # Add source node if not exists (as article)
            if source not in added_nodes:
                # Extract law code from article ID
                if source.startswith('art:'):
                    parts = source.replace('art:', '').split('/')
                    law_code = parts[0] if parts else source
                    art_num = parts[1] if len(parts) > 1 else ""
                    label = f"Art. {art_num}" if art_num else source
                else:
                    law_code = source
                    label = source

                net.add_node(
                    source,
                    label=label,
                    title=f"{source}\nFrom: {law_code}",
                    color="#74b9ff",
                    size=15,
                    shape="dot"
                )
                added_nodes.add(source)

            # Add target node if not exists
            if target not in added_nodes:
                if target.startswith('art:'):
                    parts = target.replace('art:', '').split('/')
                    law_code = parts[0] if parts else target
                    art_num = parts[1] if len(parts) > 1 else ""
                    label = f"Art. {art_num}" if art_num else target
                elif target.startswith('law:'):
                    law_code = target.replace('law:', '')
                    label = law_code
                else:
                    law_code = target
                    label = target

                net.add_node(
                    target,
                    label=label,
                    title=f"{target}\nFrom: {law_code}",
                    color="#55efc4" if target.startswith('law:') else "#fdcb6e",
                    size=20 if target.startswith('law:') else 15,
                    shape="dot"
                )
                added_nodes.add(target)

            # Add edge
            edge_color = "#e74c3c" if edge_type == "EXTERNAL_REF" else "#3498db"
            net.add_edge(
                source,
                target,
                title=edge_type,
                color=edge_color,
                width=1
            )
            edge_count += 1

            if edge_type == "INTERNAL_REF":
                internal_count += 1
            else:
                external_count += 1

        print(f"Added {edge_count} edges ({internal_count} internal, {external_count} external)")

    # Save and open
    output_path = Path(output_file)
    net.save_graph(str(output_path))
    print(f"\nGraph saved to: {output_path.absolute()}")

    # Open in browser
    import webbrowser
    webbrowser.open(f"file://{output_path.absolute()}")

    print(f"\nTotal nodes: {len(added_nodes)}")
    print("Graph opened in browser!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./lancedb_graphrag"
    visualize_graph(db_path)
