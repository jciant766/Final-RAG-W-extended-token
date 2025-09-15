import streamlit as st
import os
import json
from document_processor import DocumentProcessor
from vector_store import VectorStore
from search_engine import SearchEngine
from debug_logger import DebugLogger

# Page config
st.set_page_config(
    page_title="Malta Commercial Code Search",
    page_icon="⚖️",
    layout="centered"
)

# Initialize debug logger
debug = DebugLogger("main_app")

# Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stTextInput > label {display: none;}
    
    .search-container {
        margin: 2rem 0;
    }
    
    .result-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .article-ref {
        font-weight: bold;
        color: #1f77b4;
        font-size: 1.1rem;
    }
    
    .relevance {
        background: #e3f2fd;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.9rem;
        color: #1565c0;
    }
    
    .doc-badge {
        background: #fff3e0;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #ef6c00;
        margin-left: 0.5rem;
        white-space: nowrap;
    }
    
    .debug-panel {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 5px;
        font-family: monospace;
        font-size: 0.85rem;
    }

    /* Ensure long legal texts wrap within expanders without horizontal scroll */
    .full-article {
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-x: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Initialize system
@st.cache_resource
def init_system():
    """Initialize search system"""
    debug.log("info", "Initializing system")
    
    if not os.path.exists("chroma_db"):
        with st.spinner("First time setup - processing legal document..."):
            processor = DocumentProcessor()
            processor.process_document("malta_commercial_code_text.txt")
    
    vector_store = VectorStore()
    search_engine = SearchEngine(vector_store, enable_ai_overview=True)
    
    debug.log("info", "System initialized successfully")
    return search_engine

# Header
st.title("⚖️ Malta Commercial Code Search")
st.markdown("*Smart legal search with automatic query understanding*")

# Debug mode toggle (hidden)
if st.session_state.get('debug_clicks', 0) >= 3:
    debug_mode = st.checkbox("🔧 Debug Mode", key="debug_mode")
else:
    debug_mode = False

# Click counter for debug mode
col1, col2, col3 = st.columns([1, 8, 1])
with col3:
    if st.button("⚙️", key="settings"):
        st.session_state['debug_clicks'] = st.session_state.get('debug_clicks', 0) + 1

# Initialize system
search_engine = init_system()

# Search interface
with st.container():
    query = st.text_input(
        "search",
        placeholder="Search articles or ask questions...",
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        search_button = st.button("Search", type="primary", use_container_width=True)

# Search handling
if query and search_button:
    debug.log("query", query)
    
    with st.spinner("Searching..."):
        search_payload = search_engine.search(query)
    
    # Results display
    results = []
    ai_overview = None
    query_analysis = {}
    if isinstance(search_payload, dict):
        results = search_payload.get('results', []) or []
        ai_overview = search_payload.get('ai_overview')
        query_analysis = search_payload.get('query_analysis') or {}
    else:
        results = search_payload or []
    
    if results:
        st.markdown("---")
        st.markdown(f"**Found {len(results)} relevant results:**")

        # Detected intent
        if isinstance(query_analysis, dict):
            intent = query_analysis.get('intent')
            intent_map = {
                'definition': 'Definition',
                'procedural': 'Procedure',
                'penalty': 'Penalty / Offence',
                'requirement': 'Requirement / Obligation',
                'temporal': 'Timing / Deadline'
            }
            intent_text = intent_map.get(intent, 'General information')
            st.caption(f"Detected intent: {intent_text}")
        
        # Optional AI overview
        if ai_overview and isinstance(ai_overview, dict) and ai_overview.get('overview'):
            st.markdown("#### AI Overview")
            # Main overview text
            st.write(ai_overview['overview'])
            
            # Confidence badge (optional)
            conf = ai_overview.get('confidence')
            if isinstance(conf, (int, float)):
                st.caption(f"Confidence: {conf:.0%}")
            
            # Sources list
            citations = ai_overview.get('citations') or []
            if citations:
                st.markdown("**Sources**")
                for c in citations:
                    doc = c.get('document', '')
                    cit = c.get('citation', '')
                    page = c.get('page')
                    # Always show page number if it's a valid positive integer
                    page_str = ""
                    if page is not None:
                        try:
                            page_num = int(page)
                            if page_num >= 1:
                                page_str = f" (Page {page_num})"
                        except (ValueError, TypeError):
                            pass
                    st.markdown(f"- {doc} — {cit}{page_str}")
        
        for i, result in enumerate(results):
            # Result card
            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <div>
                        <span class="article-ref">{result['citation'].split(',')[0]}</span>
                        <span class="doc-badge">{result.get('metadata', {}).get('document', '')}</span>
                    </div>
                    <span class="relevance">{result['score']:.0%} match</span>
                </div>
                <div>{result['content'][:400]}...</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expandable full content - always show expander
            with st.expander(f"Read full article - {result['citation'].split(',')[0]}"):
                st.markdown(f"<div class='full-article'>{result['content']}</div>", unsafe_allow_html=True)
                
                # Debug info
                if debug_mode:
                    st.json({
                        'article': result['metadata']['article'],
                        'tokens': result['metadata'].get('tokens', 'N/A'),
                        'chunk': f"{result['metadata'].get('chunk_index', 0) + 1}/{result['metadata'].get('total_chunks', 1)}",
                        'page': result['metadata']['page']
                    })
    else:
        st.info("No results found. Try different keywords or check the debug log.")

# Debug panel
if debug_mode:
    st.markdown("---")
    st.markdown("### 🔍 Debug Information")
    
    tabs = st.tabs(["Recent Logs", "Query Analysis", "System Stats"])
    
    with tabs[0]:
        # Recent logs
        logs = DebugLogger.get_recent_logs(n=20)
        for log in logs:
            level_color = {
                'error': '#d32f2f',
                'info': '#1976d2',
                'debug': '#388e3c',
                'query': '#f57c00'
            }.get(log['level'], '#666')
            
            st.markdown(f"""
            <div class="debug-panel">
                <span style="color: {level_color};">[{log['level'].upper()}]</span>
                <span>{log['timestamp']}</span>
                <span>{log['module']}</span>: {log['message']}
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[1]:
        # Query analysis
        analysis = DebugLogger.analyze_queries()
        st.json(analysis)
    
    with tabs[2]:
        # System stats
        if os.path.exists('processing_report.json'):
            with open('processing_report.json', 'r') as f:
                stats = json.load(f)
            st.json(stats)

# Help section
with st.expander("📚 Search Tips"):
    st.markdown("""
    **Query Examples:**
    - `Article 477` - Direct article lookup
    - `bankruptcy procedures` - Topic search
    - `What are the penalties for late payment?` - Natural questions
    - `requirements for public broker` - Concept search
    
    **System Features:**
    - Automatic query type detection
    - Smart chunking for long articles
    - Token-aware processing
    - Debug mode for troubleshooting
    """)
