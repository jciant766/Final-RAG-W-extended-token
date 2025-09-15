import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import random
import json

# Optional typing and search imports
from typing import Dict
try:
    from search_engine import SearchEngine
    from vector_store import VectorStore
    SEARCH_AVAILABLE = True
except Exception:
    SEARCH_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Malta Legal Monitor Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #2a5298;
        margin-bottom: 1rem;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active { background-color: #28a745; }
    .status-processing { background-color: #ffc107; }
    .status-error { background-color: #dc3545; }
    .status-idle { background-color: #6c757d; }
    .status-retrying { background-color: #17a2b8; animation: pulse 1s infinite; }
    
    /* Live activity animations */
    .live-indicator { animation: blink 1s steps(2, start) infinite; }
    
    .document-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #17a2b8;
        margin-bottom: 0.5rem;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #2a5298, #1e3c72);
    }
    
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Fullscreen loading overlay */
    .overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.96);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .overlay-card {
        width: min(820px, 92vw);
        background: white;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border: 1px solid #e9ecef;
    }
    .spinner {
        width: 36px; height: 36px;
        border: 4px solid #e9ecef;
        border-top-color: #2a5298;
        border-radius: 50%;
        margin-right: 10px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes pulse { 0% { transform: scale(1); opacity: 1;} 50% { transform: scale(1.1); opacity: 0.7;} 100% { transform: scale(1); opacity: 1;} }
    @keyframes blink { 50% { opacity: 0.2; } }
    .spinner { animation: spin 0.9s linear infinite; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'documents_found' not in st.session_state:
    st.session_state.documents_found = []
if 'processing_stats' not in st.session_state:
    st.session_state.processing_stats = {
        'total_documents': 0,
        'processed_today': 0,
        'processing_rate': 0,
        'success_rate': 94.2
    }
if 'system_phase' not in st.session_state:
    st.session_state.system_phase = 'idle'  # idle | starting | running
if 'startup_pending' not in st.session_state:
    st.session_state.startup_pending = False
if 'startup_done' not in st.session_state:
    st.session_state.startup_done = False
if 'startup_target_duration_s' not in st.session_state:
    st.session_state.startup_target_duration_s = 5.0
if 'startup_start_time' not in st.session_state:
    st.session_state.startup_start_time = None
if 'pending_notifications' not in st.session_state:
    st.session_state.pending_notifications = []
if 'trend' not in st.session_state:
    base_time = datetime.now()
    st.session_state.trend = {
        'times': [base_time - timedelta(hours=i) for i in range(24, 0, -1)],
        'values': [random.randint(0, 4) for _ in range(24)]
    }
if 'repository_stats' not in st.session_state:
    # Preloaded repository snapshot to convey data already exists
    def _repo_row(total_low, total_high):
        total = random.randint(total_low, total_high)
        last24 = random.randint(6, 48)
        backlog = random.randint(0, 35)
        error_rate = round(random.uniform(0.4, 1.6), 2)
        return {
            'total': total,
            'last_24h': last24,
            'backlog': backlog,
            'error_rate': error_rate
        }
    st.session_state.repository_stats = {
        'Legislation Malta (legislation.mt)': _repo_row(2500, 7000),
        'MFSA - Malta Financial Services Authority': _repo_row(1800, 5200),
        'Government Gazette Malta': _repo_row(3600, 9000),
        'Registry of Companies (ROC)': _repo_row(2100, 6800),
        'Malta Courts - Commercial Court': _repo_row(420, 1300),
        'Malta Courts - Court of Appeal': _repo_row(240, 900),
        'EU Company Law Directives': _repo_row(120, 480),
        'Malta Business Registry': _repo_row(900, 2400)
    }
    st.session_state.total_indexed_documents = sum(v['total'] for v in st.session_state.repository_stats.values())
if 'pipeline_progress' not in st.session_state:
    st.session_state.pipeline_progress = {
        'discovery': random.randint(0, 20),
        'ocr': random.randint(0, 15),
        'extract': random.randint(0, 10),
        'index': random.randint(0, 5)
    }
if 'search_active' not in st.session_state:
    st.session_state.search_active = False
if 'last_live_tick' not in st.session_state:
    st.session_state.last_live_tick = time.time()

# Cached search system (vector database)
@st.cache_resource(show_spinner=False)
def init_search_system():
    if not SEARCH_AVAILABLE:
        return None
    try:
        vector_store = VectorStore()
        search_engine = SearchEngine(vector_store, enable_ai_overview=False)
        return search_engine
    except Exception as e:
        st.session_state.search_init_error = str(e)
        return None

# Authentic Malta legal sources based on actual monitoring requirements
MALTA_LEGAL_SOURCES = [
    "Legislation Malta (legislation.mt)",
    "MFSA - Malta Financial Services Authority",
    "Government Gazette Malta",
    "Registry of Companies (ROC)",
    "Malta Courts - Commercial Court",
    "Malta Courts - Court of Appeal",
    "EU Company Law Directives",
    "Malta Business Registry"
]

DOCUMENT_TYPES = [
    "Legal Notice",
    "MFSA Circular",
    "MFSA Directive", 
    "ROC Practice Note",
    "Commercial Court Judgment",
    "Court of Appeal Ruling",
    "Companies Act Amendment",
    "EU Directive Implementation",
    "Technical Guidance",
    "Policy Update",
    "Administrative Circular",
    "Constitutional Court Decision"
]

def generate_realistic_document():
    """Generate realistic Malta legal document data based on actual legal system"""
    source = random.choice(MALTA_LEGAL_SOURCES)
    doc_type = random.choice(DOCUMENT_TYPES)
    
    # Generate realistic references based on document type
    if doc_type == "Legal Notice":
        ref_number = f"L.N. {random.randint(200, 400)} of {datetime.now().year}"
        titles = [
            f"Companies Act (Cap. 386) - Amendment Regulations {ref_number}",
            f"Beneficial Ownership Reporting Requirements {ref_number}",
            f"Digital Filing Procedures {ref_number}",
            f"Directors' Duties and Responsibilities {ref_number}",
            f"Audit Requirements for Small Companies {ref_number}"
        ]
    elif doc_type == "MFSA Circular":
        ref_number = f"MFSA/CIR/{random.randint(20, 50):02d}/{datetime.now().year}"
        titles = [
            f"Beneficial Ownership Requirements - {ref_number}",
            f"Anti-Money Laundering Compliance - {ref_number}",
            f"Corporate Governance Standards - {ref_number}",
            f"Financial Reporting Deadlines - {ref_number}",
            f"Risk Management Framework - {ref_number}"
        ]
    elif doc_type == "MFSA Directive":
        ref_number = f"MFSA/DIR/{random.randint(10, 30):02d}/{datetime.now().year}"
        titles = [
            f"Directive on Shareholder Rights - {ref_number}",
            f"Market Abuse Prevention - {ref_number}",
            f"Transparency Requirements - {ref_number}",
            f"Audit Committee Composition - {ref_number}",
            f"Whistleblowing Procedures - {ref_number}"
        ]
    elif doc_type == "ROC Practice Note":
        ref_number = f"ROC/PN/{random.randint(5, 25):02d}/{datetime.now().year}"
        titles = [
            f"Digital Filing System Updates - {ref_number}",
            f"Annual Return Submission - {ref_number}",
            f"Company Name Reservation - {ref_number}",
            f"Statutory Register Requirements - {ref_number}",
            f"Strike-off Procedures - {ref_number}"
        ]
    elif "Court" in doc_type:
        ref_number = f"Court Case {random.randint(1000, 9999)}/{datetime.now().year}"
        titles = [
            f"Director Liability for Breach of Fiduciary Duty - {ref_number}",
            f"Shareholder Oppression Remedy - {ref_number}",
            f"Company Winding-up Proceedings - {ref_number}",
            f"Minority Shareholder Rights - {ref_number}",
            f"Insolvency and Corporate Rescue - {ref_number}"
        ]
    elif doc_type == "EU Directive Implementation":
        ref_number = f"EU/IMP/{random.randint(1, 15):02d}/{datetime.now().year}"
        titles = [
            f"Shareholder Rights Directive Implementation - {ref_number}",
            f"Audit Directive Transposition - {ref_number}",
            f"Transparency Directive Updates - {ref_number}",
            f"Market Abuse Regulation Compliance - {ref_number}",
            f"Corporate Sustainability Reporting - {ref_number}"
        ]
    else:
        ref_number = f"DOC/{random.randint(100, 999)}/{datetime.now().year}"
        titles = [
            f"Updated {doc_type} Guidelines - {ref_number}",
            f"New {doc_type} Requirements - {ref_number}",
            f"Revision of {doc_type} Standards - {ref_number}",
            f"Clarification on {doc_type} Provisions - {ref_number}"
        ]
    
    # Determine priority based on document type
    if doc_type in ["Legal Notice", "MFSA Directive", "Court of Appeal Ruling"]:
        priority = random.choices(['High', 'Medium'], weights=[70, 30])[0]
    elif doc_type in ["MFSA Circular", "Commercial Court Judgment"]:
        priority = random.choices(['High', 'Medium', 'Low'], weights=[40, 45, 15])[0]
    else:
        priority = random.choices(['High', 'Medium', 'Low'], weights=[20, 50, 30])[0]
    
    return {
        'timestamp': datetime.now() - timedelta(minutes=random.randint(1, 60)),
        'source': source,
        'title': random.choice(titles),
        'reference': ref_number,
        'type': doc_type,
        'status': random.choice(['Processing', 'Completed', 'Pending Review']),
        'priority': priority,
        'pages': random.randint(5, 150),
        'size_mb': round(random.uniform(0.5, 25.0), 2)
    }

def run_startup_sequence():
    """Progressive startup animation with connection steps and messages."""
    st.session_state.system_phase = 'starting'
    start = time.time()
    if not st.session_state.startup_start_time:
        st.session_state.startup_start_time = start
    with st.status("Initializing monitoring services...", expanded=True) as status:
        sources = [
            "Legislation Malta (legislation.mt)",
            "MFSA - Malta Financial Services Authority",
            "Government Gazette Malta",
            "Registry of Companies (ROC)",
            "Malta Courts"
        ]
        st.write("Bootstrapping components: scheduler, OCR, extractor, indexer...")
        while time.time() - start < st.session_state.startup_target_duration_s:
            for src in sources:
                if time.time() - start >= st.session_state.startup_target_duration_s:
                    break
                status.update(label=f"Connecting to {src}...", state="running")
                st.write(f"{src}: establishing secure connection")
                time.sleep(random.uniform(0.25, 0.6))
                if random.random() < 0.18:
                    st.write(f"{src}: transient network issue detected — retrying...")
                    time.sleep(random.uniform(0.2, 0.5))
                st.write(f"{src}: connected")
        st.write("Verifying credentials and loading last-run state")
        time.sleep(random.uniform(0.2, 0.5))
        status.update(label="System online. Monitoring started.", state="complete")
    st.session_state.startup_pending = False
    st.session_state.startup_done = True
    st.session_state.system_phase = 'running'


def update_simulation():
    """Update simulation data with realistic fluctuations and notifications."""
    if not st.session_state.simulation_running:
        return

    processed_this_tick = 0

    # Occasionally add a discovered document
    if random.random() < 0.4:
        new_doc = generate_realistic_document()
        new_doc['status'] = random.choice(['Processing', 'Pending Review'])
        st.session_state.documents_found.insert(0, new_doc)
        st.session_state.pending_notifications.append({
            'msg': f"Document discovered: {new_doc['title']} ({new_doc['source']})",
            'icon': '📄'
        })
        st.session_state.processing_stats['total_documents'] += 1
        if len(st.session_state.documents_found) > 80:
            st.session_state.documents_found = st.session_state.documents_found[:80]

    # Advance processing statuses and simulate occasional retries
    for doc in st.session_state.documents_found:
        roll = random.random()
        if doc['status'] == 'Processing' and roll < 0.35:
            doc['status'] = 'Completed'
            processed_this_tick += 1
        elif doc['status'] in ['Pending Review', 'Retrying'] and roll < 0.25:
            doc['status'] = 'Processing'
        elif roll < 0.04:
            doc['status'] = 'Retrying'
            st.session_state.pending_notifications.append({
                'msg': f"Retrying {doc['type']} from {doc['source']}",
                'icon': '🔁'
            })

    # Update counters and metrics with realistic jitter
    st.session_state.processing_stats['processed_today'] += processed_this_tick
    rate = st.session_state.processing_stats['processing_rate'] or random.uniform(1.5, 3.0)
    rate = max(0.5, min(6.0, rate + random.uniform(-0.25, 0.35)))
    st.session_state.processing_stats['processing_rate'] = rate

    success = st.session_state.processing_stats['success_rate'] or 94.2
    target = 94.5 + random.uniform(-1.2, 1.2)
    success += (target - success) * 0.2 + random.uniform(-0.15, 0.15)
    st.session_state.processing_stats['success_rate'] = max(92.0, min(97.5, success))

    # Update trend data for charts
    st.session_state.trend['times'].append(datetime.now())
    st.session_state.trend['values'].append(max(0, processed_this_tick + random.randint(0, 3)))
    if len(st.session_state.trend['times']) > 24:
        st.session_state.trend['times'] = st.session_state.trend['times'][-24:]
        st.session_state.trend['values'] = st.session_state.trend['values'][-24:]

    # Animate pipeline progress bars
    def _step(val: int, low: int, high: int) -> int:
        return min(100, max(0, val + random.randint(low, high)))
    st.session_state.pipeline_progress['discovery'] = _step(st.session_state.pipeline_progress['discovery'], 6, 16)
    st.session_state.pipeline_progress['ocr'] = _step(st.session_state.pipeline_progress['ocr'], 5, 12)
    st.session_state.pipeline_progress['extract'] = _step(st.session_state.pipeline_progress['extract'], 4, 10)
    st.session_state.pipeline_progress['index'] = _step(st.session_state.pipeline_progress['index'], 3, 9)
    # Loop discovery bar
    if st.session_state.pipeline_progress['discovery'] >= 100:
        st.session_state.pipeline_progress['discovery'] = 0

# Preload overlay to convey existing indexed data during startup
## overlay disabled per request

# Main header
st.markdown("""
<div class="main-header">
    <h1>⚖️ Malta Legal Monitor Pro</h1>
    <p>Operational View of Indexed Malta Company Law Sources</p>
    <p style="font-size: 0.9rem; margin-top: 0.5rem; opacity: 0.9;">
        Legislation Malta • MFSA • Government Gazette • Courts • EU Directives
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🎛️ Control Panel")
    
    # Simulation controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start", key="start_btn", disabled=st.session_state.startup_pending or st.session_state.simulation_running):
            st.session_state.startup_pending = not st.session_state.startup_done
            st.session_state.simulation_running = True
            st.session_state.search_active = False
            if st.session_state.startup_pending:
                run_startup_sequence()
    
    with col2:
        if st.button("⏸️ Pause", key="pause_btn", disabled=st.session_state.startup_pending or not st.session_state.simulation_running):
            st.session_state.simulation_running = False
    
    st.markdown("---")
    
    # Filters
    st.markdown("### 🔍 Filters")
    
    selected_sources = st.multiselect(
        "Legal Sources",
        MALTA_LEGAL_SOURCES,
        default=MALTA_LEGAL_SOURCES[:4]
    )
    
    selected_types = st.multiselect(
        "Document Types",
        DOCUMENT_TYPES,
        default=DOCUMENT_TYPES[:4]
    )
    
    priority_filter = st.selectbox(
        "Priority Level",
        ["All", "High", "Medium", "Low"]
    )
    
    st.markdown("---")
    
    # Real-time status
    st.markdown("### 📊 System Status")
    
    status_color = "🟢" if st.session_state.simulation_running else "🔴"
    phase = "Starting" if st.session_state.startup_pending else ("Active" if st.session_state.simulation_running else "Idle")
    st.markdown(f"**Status:** {status_color} {phase}")
    
    st.markdown(f"**Documents Found:** {len(st.session_state.documents_found)}")
    st.markdown(f"**Processing Rate:** {st.session_state.processing_stats['processing_rate']:.1f} docs/min")
    st.markdown(f"**Success Rate:** {st.session_state.processing_stats['success_rate']:.1f}%")
    
    st.markdown("---")
    
    # Source descriptions
    st.markdown("### 📋 Monitored Sources")
    st.markdown("**Government Sources:**")
    st.markdown("• Legislation Malta (legislation.mt)")
    st.markdown("• MFSA Circulars & Directives")
    st.markdown("• Government Gazette")
    st.markdown("• Registry of Companies")
    
    st.markdown("**Court Sources:**")
    st.markdown("• Commercial Court")
    st.markdown("• Court of Appeal")
    
    st.markdown("**EU Sources:**")
    st.markdown("• Company Law Directives")
    st.markdown("• Implementation Updates")

# Main content area
# Prominent global search bar (connected to vector DB)
search_engine = init_search_system()
st.markdown("### 🔎 Search the Indexed Corpus")
search_cols = st.columns([7, 1])
with search_cols[0]:
    main_query = st.text_input(
        "Search",
        key="main_search",
        placeholder="Search articles or ask questions...",
        label_visibility="collapsed"
    )
with search_cols[1]:
    do_search = st.button("Search", type="primary", use_container_width=True)

search_error = st.session_state.get('search_init_error') if SEARCH_AVAILABLE else "Vector search unavailable in this environment."
if do_search and main_query:
    st.session_state.search_active = True
    if search_engine is None:
        st.error(f"Search initialization failed: {search_error}")
    else:
        with st.spinner("Querying vector database..."):
            payload = search_engine.search(main_query, max_results=5, include_ai_overview=False)
        results = payload.get('results', []) if isinstance(payload, dict) else (payload or [])
        if results:
            st.markdown(f"**Found {len(results)} results**")
            for r in results:
                st.markdown(f"""
<div class="result-card">
  <div class="result-header">
    <div><span class="article-ref">{r['citation'].split(',')[0]}</span> <span class="doc-badge">{r.get('metadata', {}).get('document', '')}</span></div>
    <span class="relevance">{r['score']:.0%} match</span>
  </div>
  <div>{r['content'][:400]}...</div>
</div>
""", unsafe_allow_html=True)
                with st.expander(f"Read full article - {r['citation'].split(',')[0]}"):
                    st.text(r['content'])
        else:
            st.info("No results found. Try different keywords.")

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    # KPI Metrics
    st.markdown("### 📈 Key Performance Indicators")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        # Animate the counter if simulation is running
        if st.session_state.simulation_running and random.random() < 0.3:
            st.session_state.processing_stats['total_documents'] += 1
        
        st.metric(
            label="Documents Found Today",
            value=st.session_state.processing_stats['total_documents'],
            delta=f"+{random.randint(1, 5)} from yesterday"
        )
    
    with kpi_col2:
        # small jitter to keep value moving
        # no animation: keep the number static unless user interacts
        st.metric(
            label="Processing Speed",
            value=f"{st.session_state.processing_stats['processing_rate']:.1f}",
            delta="docs/min"
        )
    
    with kpi_col3:
        st.metric(
            label="Success Rate",
            value=f"{st.session_state.processing_stats['success_rate']:.1f}%",
            delta=""
        )
    
    with kpi_col4:
        st.metric(
            label="Indexed Corpus",
            value=f"{st.session_state.total_indexed_documents:,}",
            delta="documents"
        )
    
    st.markdown("---")
    
    # Real-time monitoring progress
    st.markdown("### 🔄 Real-time Monitoring")
    
    if st.session_state.simulation_running:
        # Animated progress bars for different tasks
        col_prog1, col_prog2 = st.columns(2)
        
        with col_prog1:
            st.markdown("**Document Discovery** <span class='live-indicator'>●</span>", unsafe_allow_html=True)
            st.progress(st.session_state.pipeline_progress['discovery'])
            
            st.markdown("**OCR Processing** <span class='live-indicator'>●</span>", unsafe_allow_html=True)
            st.progress(st.session_state.pipeline_progress['ocr'])
            
        with col_prog2:
            st.markdown("**Text Extraction** <span class='live-indicator'>●</span>", unsafe_allow_html=True)
            st.progress(st.session_state.pipeline_progress['extract'])
            
            st.markdown("**Vector Indexing** <span class='live-indicator'>●</span>", unsafe_allow_html=True)
            st.progress(st.session_state.pipeline_progress['index'])
    else:
        # Show idle status
        st.markdown("""
        <div style="background: linear-gradient(90deg, #6c757d, #adb5bd); color: white; padding: 0.5rem 1rem; border-radius: 5px; margin-bottom: 1rem; text-align: center;">
            <strong>⏸️ MONITORING PAUSED</strong> - Click "Start" to begin real-time document discovery
        </div>
        """, unsafe_allow_html=True)
        
        # Show static progress bars at 0%
        col_prog1, col_prog2 = st.columns(2)
        
        with col_prog1:
            st.markdown("**Document Discovery**")
            st.progress(0)
            
            st.markdown("**OCR Processing**")
            st.progress(0)
            
        with col_prog2:
            st.markdown("**Text Extraction**")
            st.progress(0)
            
            st.markdown("**Vector Indexing**")
            st.progress(0)
    
    # Recent documents table
    st.markdown("### 📄 Recently Discovered Documents")
    
    if st.session_state.documents_found:
        df = pd.DataFrame(st.session_state.documents_found)
        
        # Filter data based on sidebar selections
        if selected_sources:
            df = df[df['source'].isin(selected_sources)]
        if selected_types:
            df = df[df['type'].isin(selected_types)]
        if priority_filter != "All":
            df = df[df['priority'] == priority_filter]
        
        # Display as styled list with badges and live timestamps
        for idx, row in df.head(10).iterrows():
            status_class = {
                'Processing': 'status-processing',
                'Completed': 'status-active',
                'Pending Review': 'status-idle',
                'Retrying': 'status-retrying'
            }.get(row['status'], 'status-idle')
            
            st.markdown(f"""
            <div class="document-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; color: #2a5298;">{row['title']}</h4>
                        <p style="margin: 0.5rem 0; color: #6c757d;">{row['source']} • {row['reference']}</p>
                        <p style="margin: 0; font-size: 0.9rem;">
                            <span class="status-indicator {status_class}"></span>
                            {row['status']} • {row['priority']} Priority • {row['pages']} pages • {row['size_mb']} MB
                        </p>
                    </div>
                    <div style="text-align: right; color: #6c757d; font-size: 0.8rem;">
                        {datetime.now().strftime('%H:%M:%S')}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        # Show notifications
        if st.session_state.pending_notifications:
            for note in st.session_state.pending_notifications[-3:]:
                st.toast(note['msg'], icon=note['icon'])
            st.session_state.pending_notifications = st.session_state.pending_notifications[-5:]
    else:
        st.info("No documents discovered yet. Start the monitoring simulation to see real-time document discovery.")

with col2:
    # Monitoring statistics charts
    st.markdown("### 📊 Monitoring Statistics")
    
    # Source activity from repository snapshot (preloaded corpus)
    source_counts = {k: v['total'] for k, v in st.session_state.repository_stats.items()}
    
    if source_counts:
        fig_sources = px.pie(
            values=list(source_counts.values()),
            names=list(source_counts.keys()),
            title="Document Sources",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_sources.update_layout(height=300)
        st.plotly_chart(fig_sources, use_container_width=True)
    
    # Processing trends
    st.markdown("### 📈 Processing Trends")
    
    # Use live trend data from session state
    hours = st.session_state.trend['times']
    trend_data = st.session_state.trend['values']
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=hours,
        y=trend_data,
        mode='lines+markers',
        name='Documents/Hour',
        line=dict(color='#2a5298', width=3),
        marker=dict(size=6)
    ))
    
    fig_trend.update_layout(
        title="Documents Processed (Last 24h)",
        xaxis_title="Time",
        yaxis_title="Documents",
        height=250,
        showlegend=False
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Status distribution
    st.markdown("### 🎯 Status Distribution")
    
    status_counts = {}
    for doc in st.session_state.documents_found:
        status = doc['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    if status_counts:
        fig_status = px.bar(
            x=list(status_counts.keys()),
            y=list(status_counts.values()),
            title="Document Status",
            color=list(status_counts.keys()),
            color_discrete_map={
                'Processing': '#ffc107',
                'Completed': '#28a745',
                'Pending Review': '#17a2b8'
            }
        )
        fig_status.update_layout(height=250, showlegend=False)
        st.plotly_chart(fig_status, use_container_width=True)

# Auto-refresh while simulation is running
if st.session_state.simulation_running:
    update_simulation()
    if not st.session_state.search_active:
        time.sleep(random.uniform(0.8, 1.4))
        st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 2rem;">
    <p><strong>Malta Legal Monitor Pro</strong> • Professional Company Law Monitoring Platform</p>
    <p>Monitoring Legislation Malta, MFSA, Government Gazette, Courts & EU Directives</p>
    <p>Powered by Advanced AI & Machine Learning • Real-time Processing • 99.9% Uptime</p>
</div>
""", unsafe_allow_html=True)
