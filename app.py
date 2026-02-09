"""
Streamlit UI for Maltese Law RAG System.

Features:
- GraphRAG: Category classification + hierarchical search + graph expansion
- Multi-query retrieval for +7-14% recall
- Voyage rerank-2 with relevance threshold filtering
- Claude Sonnet for response generation with Anthropic Citations API
"""

import streamlit as st
import time
import re
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# Import components
from src.retrieval.graphrag_retriever import GraphRAGRetriever
from src.retrieval.reranker import VoyageReranker
from src.retrieval.enhanced_pipeline import EnhancedRetrievalPipeline
from src.generation.response_generator import LegalResponseGenerator

# Build law_code -> PDF filename lookup from static folder
PDF_LOOKUP = {}
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    for fname in os.listdir(_static_dir):
        if fname.endswith(".pdf"):
            # Extract law code from filename like "Companies Act (Cap. 386).pdf"
            m = re.search(r'\(((?:Cap\.|S\.L\.)\s*[\d.]+)\)', fname)
            if m:
                PDF_LOOKUP[m.group(1)] = fname


PDF_SERVER = "http://localhost:5000/static"


def law_code_to_url(law_code: str, article_number: str = None) -> str:
    """Convert a law code to a URL pointing to the PDF server."""
    code = law_code.strip()
    if code in PDF_LOOKUP:
        return f"{PDF_SERVER}/{quote(PDF_LOOKUP[code])}"
    return ""


def linkify_law_references(text: str) -> str:
    """Replace law/article references in text with clickable PDF links."""
    def replace_match(m):
        full = m.group(0)
        law_code = m.group(1)
        url = law_code_to_url(law_code)
        if url:
            return f'<a href="{url}" target="_blank">{full}</a>'
        return full

    pattern = r'((?:Cap\.|S\.L\.)\s*[\d.]+)(?:,?\s*[Aa]rticle\s+((\d+[A-Za-z]?)))?'
    return re.sub(pattern, replace_match, text)


# Page config
st.set_page_config(
    page_title="Maltese Law RAG",
    page_icon="",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .citation-box {
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.9em;
        color: #1a1a1a;
    }
    .citation-box a {
        color: #1565c0;
        text-decoration: none;
        font-weight: 600;
    }
    .citation-box a:hover {
        text-decoration: underline;
    }
    .response-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin: 16px 0;
        color: #1a1a1a;
    }
    .response-box a {
        color: #1565c0;
        text-decoration: none;
    }
    .response-box a:hover {
        text-decoration: underline;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 16px;
        border-radius: 8px;
        text-align: center;
    }
    .category-tag {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 4px 12px;
        border-radius: 16px;
        margin: 2px;
        font-size: 0.85em;
    }
    .law-tag {
        display: inline-block;
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 12px;
        border-radius: 16px;
        margin: 2px;
        font-size: 0.85em;
    }
    .routing-info {
        background-color: #fff3e0;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


# Initialize components
@st.cache_resource
def init_system():
    """Initialize all RAG components."""
    try:
        retriever = GraphRAGRetriever(db_path="./lancedb_graphrag")
    except ValueError as e:
        return None, None, None, str(e)

    reranker = VoyageReranker()
    pipeline = EnhancedRetrievalPipeline(reranker=reranker)
    generator = LegalResponseGenerator()

    return retriever, pipeline, generator, "ready"


# Main app
def main():
    st.title("Maltese Law Research Assistant")
    st.markdown("*Search across 600+ chapters of Maltese legislation with AI-powered retrieval*")

    # Initialize system
    try:
        retriever, pipeline, generator, status = init_system()

        if status != "ready":
            st.warning(f"System not ready: {status}")
            st.code("python scripts/ingest_json_extractions.py", language="bash")
            return

    except Exception as e:
        st.error(f"Failed to initialize system: {e}")
        return

    # Sidebar settings
    with st.sidebar:
        st.header("Settings")

        st.subheader("Retrieval")

        use_multi_query = st.checkbox(
            "Multi-Query Retrieval",
            value=True,
            help="Search with multiple query phrasings for better recall (+7-14%)"
        )

        use_reranking = st.checkbox(
            "Reranking (Recommended)",
            value=True,
            help="Use Voyage rerank-2 with relevance filtering"
        )

        use_graph_expansion = st.checkbox(
            "Graph Expansion",
            value=True,
            help="Follow cross-references to find related articles"
        )

        num_articles = st.slider("Articles to retrieve", 5, 50, 30)
        num_rerank = st.slider("Articles after reranking", 3, 10, 5)
        top_laws = st.slider("Laws to search", 5, 20, 15)

        st.subheader("Manual Filter (Optional)")
        law_filter_input = st.text_input(
            "Law Code",
            "",
            help="e.g., Cap. 386 for Companies Act, S.L. 65.11 for Motor Vehicles"
        )

        st.markdown("---")
        tables = list(retriever.tables.keys())
        st.markdown(f"**Tables:** {', '.join(tables)}")
        if 'articles' in retriever.tables:
            count = retriever.tables['articles'].count_rows()
            st.markdown(f"**Articles indexed:** {count}")

    # Main search interface
    query = st.text_area(
        "Ask a question about Maltese law:",
        placeholder="e.g., What are the requirements for registering a company in Malta?",
        height=100
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    # Process query
    if search_clicked and query:
        with st.spinner("Searching laws..."):
            start_time = time.time()

            # Determine law filter
            law_filter = law_filter_input.strip() if law_filter_input.strip() else None

            # Multi-query: generate variants
            if use_multi_query:
                query_variants = pipeline.generate_query_variants(query)
            else:
                query_variants = [query]

            # Search with each variant and merge results
            all_articles = []
            seen_ids = set()
            classification_info = None
            laws_searched = []
            query_expansion = None

            for variant in query_variants:
                search_results = retriever.search(
                    query=variant,
                    limit=num_articles,
                    top_laws=top_laws,
                    expand_graph=use_graph_expansion,
                    auto_classify=True,
                    law_filter=law_filter
                )

                # Collect unique articles
                for art in search_results.get('articles', []):
                    art_id = art.get('id', '')
                    if art_id not in seen_ids:
                        seen_ids.add(art_id)
                        all_articles.append(art)

                # Also collect graph-expanded articles
                for art in search_results.get('related_articles', []):
                    art_id = art.get('id', '')
                    if art_id not in seen_ids:
                        seen_ids.add(art_id)
                        all_articles.append(art)

                # Keep first variant's metadata (it's the original query)
                if classification_info is None:
                    classification_info = search_results.get('classification')
                    laws_searched = search_results.get('laws_searched', [])
                    query_expansion = search_results.get('query_expansion')

            # Fundamental law boost: dedicated search for large foundational laws
            # (Cap. 9, Cap. 16, Cap. 12) that may be underrepresented in results
            from src.retrieval.graphrag_retriever import FUNDAMENTAL_LAWS
            large_laws = {'Cap. 9', 'Cap. 16', 'Cap. 12'}
            if classification_info and classification_info.get('categories') and not law_filter:
                for cat in classification_info['categories']:
                    for fund_law in FUNDAMENTAL_LAWS.get(cat, []):
                        if fund_law not in large_laws:
                            continue
                        existing = sum(1 for a in all_articles if a.get('law_code') == fund_law)
                        if existing < 8:
                            focused = retriever.search(
                                query=query, limit=15, top_laws=1,
                                expand_graph=False, auto_classify=False,
                                law_filter=fund_law
                            )
                            for art in focused.get('articles', []):
                                art_id = art.get('id', '')
                                if art_id not in seen_ids:
                                    seen_ids.add(art_id)
                                    all_articles.append(art)

            search_time = time.time() - start_time

            # Show routing info
            if classification_info or laws_searched:
                st.markdown('<div class="routing-info">', unsafe_allow_html=True)

                if classification_info and classification_info.get('categories'):
                    cats = classification_info['categories']
                    st.markdown("**Categories detected:** " + " ".join(
                        f'<span class="category-tag">{c.replace("_", " ").title()}</span>'
                        for c in cats
                    ), unsafe_allow_html=True)

                if laws_searched:
                    st.markdown(f"**Searched {len(laws_searched)} laws:** " + " ".join(
                        f'<span class="law-tag">{lc}</span>'
                        for lc in laws_searched[:8]
                    ) + (f" *+{len(laws_searched)-8} more*" if len(laws_searched) > 8 else ""),
                    unsafe_allow_html=True)

                if query_expansion and query_expansion.get('terms_added'):
                    st.markdown(f"**Terms expanded:** {', '.join(query_expansion['terms_added'])}")

                if use_multi_query and len(query_variants) > 1:
                    st.markdown(f"**Multi-query:** {len(query_variants)} variants, {len(all_articles)} unique articles found")

                st.markdown('</div>', unsafe_allow_html=True)

            # Reranking with relevance threshold
            if use_reranking and all_articles:
                rerank_start = time.time()
                results = pipeline.rerank_and_filter(
                    query, all_articles,
                    top_k=num_rerank,
                    min_relevance=0.25
                )
                rerank_time = time.time() - rerank_start
            else:
                results = all_articles[:num_rerank]
                rerank_time = 0

            # Generation
            if results:
                gen_start = time.time()
                response_data = generator.generate(query, results)
                gen_time = time.time() - gen_start

                total_time = time.time() - start_time

                # Display response
                st.markdown("### Answer")
                response_html = linkify_law_references(response_data["response"])
                st.markdown(
                    f'<div class="response-box">{response_html}</div>',
                    unsafe_allow_html=True
                )

                # Display sources
                st.markdown("### Sources")
                for source in response_data.get("sources", []):
                    law_code = source.get('chapter_number', '')
                    art_num = source.get('article_number', '')
                    url = law_code_to_url(law_code, art_num)
                    if url:
                        citation_html = f'<a href="{url}" target="_blank">{source["citation"]}</a>'
                    else:
                        citation_html = source['citation']
                    st.markdown(f"""
                    <div class="citation-box">
                        <strong>{citation_html}</strong><br>
                        <em>{source.get('chapter_title', '')}</em>
                    </div>
                    """, unsafe_allow_html=True)

                # Metrics
                st.markdown("---")
                cols = st.columns(4)
                cols[0].metric("Search", f"{search_time:.2f}s")
                cols[1].metric("Rerank", f"{rerank_time:.2f}s")
                cols[2].metric("Generate", f"{gen_time:.2f}s")
                cols[3].metric("Total", f"{total_time:.2f}s")

                # Show retrieved articles
                with st.expander("View Retrieved Articles"):
                    for i, art in enumerate(results, 1):
                        score = art.get('relevance_score', art.get('_distance', 'N/A'))
                        if isinstance(score, float):
                            score_str = f"{score:.4f}"
                        else:
                            score_str = str(score)

                        law_code = art.get('law_code', 'Unknown')
                        art_num = art.get('article_number', '?')
                        title = art.get('title', '')
                        st.markdown(f"**{i}. {law_code} Article {art_num}** - {title} (score: {score_str})")
                        st.text(art.get('text', '')[:500] + "...")
                        st.markdown("---")
            else:
                st.warning("No relevant laws found. Try broadening your search or removing filters.")

    # Example queries
    st.markdown("---")
    st.markdown("### Example Queries")

    examples = [
        "What are the director's duties under the Companies Act?",
        "What is the notice period for employment termination?",
        "How is VAT calculated on imported goods?",
        "What are the requirements for a valid contract?",
        "What penalties exist for environmental violations?"
    ]

    cols = st.columns(len(examples))
    for i, (col, example) in enumerate(zip(cols, examples)):
        if col.button(example[:25] + "...", key=f"example_{i}"):
            st.session_state['query'] = example
            st.rerun()


if __name__ == "__main__":
    main()
