import streamlit as st
import os
import json
from doc_processor import DocumentProcessor
from vector_store import VectorStore
from search_engine import SearchEngine
from debug_logger import DebugLogger

# Page config
st.set_page_config(
    page_title="Malta Legal Document Search",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize debug logger
debug = DebugLogger("main_app")

# Custom CSS - Light theme with improved styling
st.markdown("""
<style>
    /* Force light theme */
    .stApp {
        background-color: #ffffff;
        color: #262730;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Search interface styling */
    .stTextInput > label {display: none;}
    
    .search-container {
        margin: 2rem 0;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        color: white;
    }
    
    .result-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        transition: transform 0.2s ease;
    }
    
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .article-ref {
        font-weight: bold;
        color: #667eea;
        font-size: 1.2rem;
    }
    
    .relevance {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .doc-badge {
        background: linear-gradient(135deg, #ff9a9e, #fecfef);
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.85rem;
        color: #8e44ad;
        margin-left: 0.5rem;
        white-space: nowrap;
        font-weight: 500;
    }
    
    .debug-panel {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        border: 1px solid #e9ecef;
    }

    /* Ensure long legal texts wrap properly */
    .full-article {
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-x: hidden;
        line-height: 1.6;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
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
st.title("⚖️ Malta Legal Document Search")
st.markdown("*Comprehensive search across Maltese legal documents with AI-powered insights*")

# Search Tips
with st.expander("💡 Search Tips & Context Optimization", expanded=False):
    st.markdown("""
    **🔍 How to Search:**
    - **Specific Articles**: "Article 123 of Civil Code" or "Art. 123 Civil Code"
    - **Legal Topics**: "company formation", "property registration", "tax obligations"
    - **Cross-Document**: "notary duties", "money laundering prevention"
    - **Procedures**: "how to register a company", "land registration process"
    
    **⚡ AI-Powered Retrieval Strategy:**
    - **Retrieve Broadly**: Set slider to 30-50+ results - AI filters what's relevant automatically
    - **Trust the AI**: With 1M+ context window, AI can process and filter 50-100 articles intelligently
    - **No Data Loss**: More results = better coverage. AI will identify the most relevant provisions
    - **Quality Filtering**: AI prioritizes directly relevant articles and ignores tangential results
    - **Cross-Document Synthesis**: AI automatically combines related provisions from multiple laws
    - **Optimal Settings**: For complex questions, use 40-60 results; for simple queries, 20-30 is fine
    
    **🏛️ Questions Based on Actual Laws in Database:**

    **Stamp Duty & Property Transfer Tax (Cap. 364):**
    1. "What is the duty rate on documents and transfers for residential property?"
    2. "How much is the stamp duty exemption for first-time buyers purchasing property before 31 December 2023?"
    3. "What are the conditions for the 200,000 euro stamp duty exemption for first-time buyers?"
    4. "What is the reduced duty rate for property transfers in Gozo under S.L. 364.12?"
    5. "What happens if I acquired a garage of less than 30 square metres - does it count as my first property?"
    6. "What is a structured arrangement for stamp duty purposes and how does the Commissioner detect it?"
    7. "What are the notice requirements for the Commissioner for Revenue on property transfers?"

    **Notarial Profession (Cap. 55):**
    8. "What are the functions and powers of notaries according to Article 2 of Cap. 55?"
    9. "Can a notary practice as an advocate or work as a bank manager at the same time?"
    10. "What powers does a notary have to issue European Certificates of Succession?"
    11. "What are the notary's obligations when receiving acts inter vivos and wills?"
    12. "Can notaries act as mediators and commissioners for oaths?"
    13. "What is the role of the Chief Notary to Government?"
    14. "What are the examination of title requirements for notaries under Article 84C?"
    15. "What are the custody and archiving obligations for notarial acts?"

    **Money Laundering Prevention (Cap. 373):**
    16. "What is the maximum penalty for money laundering offences under Article 3 of Cap. 373?"
    17. "What is an aggravated money laundering offence within a criminal organisation?"
    18. "Can someone be convicted of money laundering without proving the underlying criminal activity?"
    19. "What are the sanctions for obliged entities who commit money laundering in their professional activities?"
    20. "What additional sanctions can the Court impose on natural persons for money laundering?"
    21. "What is the fine range for money laundering when tried in the Criminal Court?"
    22. "Can a company be held liable for money laundering committed by its directors?"

    **EU Succession Regulation (650/2012):**
    23. "What matters are excluded from the scope of EU Regulation 650/2012?"
    24. "Does the EU Succession Regulation apply to succession to estates of deceased persons?"
    25. "What is the applicable law for cross-border successions under the EU Regulation?"

    **First-Time Buyers & Gozo Exemptions (S.L. 364.12):**
    26. "What is the deadline for final deed execution to qualify for first-time buyer exemption?"
    27. "Does acquisition of an undivided share of less than 25% count against first-time buyer status?"
    28. "What evidence must be submitted to the Commissioner for Revenue for first-time buyer relief?"
    29. "How does the pro-rata benefit work when acquiring a share of property?"
    30. "What is the definition of residential property for Gozo exemption purposes?"

    **Tax on Property Transfers (S.L. 123.92):**
    31. "What are the rates under the Tax on Property Transfers Rules?"
    32. "What is the reduced rate for property transfers made between 9 June 2020 and 1 January 2022?"
    33. "What conditions must be satisfied for the 1.50 euro per 100 euro reduced rate?"

    **Land Registration (Cap. 296):**
    34. "What are the requirements for land registration under Cap. 296?"
    35. "What documents must be submitted to the Land Registrar for property registration?"
    36. "What are the fees for land registration and searches?"

    **Private Residential Leases (Cap. 604):**
    37. "What are the registration requirements for private residential lease contracts?"
    38. "What are the penalties for failing to register a residential lease?"
    39. "What are tenant and landlord rights under Cap. 604?"

    **Cohabitation Act (Cap. 614):**
    40. "What is the definition of cohabitant under the Duty on Documents and Transfers Act?"
    41. "How is a cohabitation enrolled under the Cohabitation Act?"
    42. "What are the rights and obligations of registered cohabitants?"

    **Civil Procedure & Courts (Cap. 12):**
    43. "What are the civil litigation procedures under the Code of Organization and Civil Procedure?"
    44. "What are the jurisdiction requirements for civil cases?"

    **Income Tax (Cap. 123):**
    45. "What are the capital gains tax rules under S.L. 123.27?"
    46. "What exemptions exist for property transfers under the Income Tax Act?"
    47. "What are the UCA and vacant property tax provisions under S.L. 123.203?"
    """)

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
    
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        num_results = st.slider("Number of Results", min_value=10, max_value=100, value=30, step=10, 
                               help="Retrieve more results - AI will filter and synthesize the most relevant information")
    with col2:
        search_button = st.button("Search", type="primary", use_container_width=True)

# Search handling
if query and search_button:
    debug.log("query", query)
    
    with st.spinner(f"Searching across {num_results} results..."):
        search_payload = search_engine.search(query, max_results=num_results)
    
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
            st.markdown("---")
            st.markdown("### 🤖 AI Overview")
            
            # Confidence badge
            conf = ai_overview.get('confidence')
            if isinstance(conf, (int, float)):
                st.caption(f"📊 Confidence: {conf:.0%}")
            
            # Main overview text - use markdown for proper formatting
            st.markdown(ai_overview['overview'])
            
            # Sources list
            citations = ai_overview.get('citations') or []
            if citations:
                st.markdown("---")
                st.markdown("**📚 Sources Referenced:**")
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
                    st.markdown(f"- **{doc}** — {cit}{page_str}")
            
            st.markdown("---")
        
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
    
    **General Commercial Law:**
    - `What is a trader?` - Definitions
    - `trade books requirements` - Accounting obligations
    - `acts of trade` - Commercial activities
    
    **Commercial Agents & Brokers:**
    - `commercial agent duties` - Agency relationships
    - `broker requirements` - Brokerage regulations
    - `agent commissions` - Payment structures
    
    **Bills of Exchange:**
    - `bills of exchange requirements` - Commercial instruments
    - `endorsement procedures` - Transfer mechanisms
    - `acceptance of bills` - Payment obligations
    
    **Maritime Trade:**
    - `maritime insurance` - Marine coverage
    - `bills of lading` - Shipping documents
    - `general average` - Maritime law concepts
    
    **Bankruptcy:**
    - `Article 477` - Bankruptcy declaration
    - `bankruptcy trustee duties` - Insolvency procedures
    - `debt agreements` - Restructuring options
    
    **Late Payments:**
    - `late payment penalties` - Commercial transactions
    - `interest rates` - Financial obligations
    
    **System Features:**
    - Automatic query type detection
    - Smart chunking for long articles
    - Token-aware processing
    - Debug mode for troubleshooting
    """)
