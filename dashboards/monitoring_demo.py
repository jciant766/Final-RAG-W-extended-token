import time
import random
from typing import List, Dict
import streamlit as st


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


SOURCES = [
    {
        "name": "Legislation Malta",
        "examples": [
            "Commercial Code (Cap. 13) amendment – Art. 477 updated",
            "Companies Act (Cap. 386) consolidation – Title updates",
            "Subsidiary Legislation 386.03 – Schedule revised"
        ],
    },
    {
        "name": "MFSA (Malta Financial Services Authority)",
        "examples": [
            "MFSA Circular: Annual Return Filing Deadlines",
            "MFSA Guidance: Beneficial Ownership Register Clarifications",
        ],
    },
    {
        "name": "Government Gazette",
        "examples": [
            "Legal Notice 123 of 2025 – Companies Act (Fees) Regulations",
            "Legal Notice 194 of 2021 – Amendments to S.L. 386.03",
        ],
    },
    {
        "name": "Malta Business Registry (ROC)",
        "examples": [
            "ROC Notice: New e-filing specifications",
            "ROC Practice Note: Director address disclosures",
        ],
    },
]

TARGET_FILE_COUNT = 300


def generate_fake_update() -> Dict:
    source = random.choice(SOURCES)
    title = random.choice(source["examples"])
    ref = random.choice([
        "S.L. 386.03 Reg. 2",
        "S.L. 386.02 Reg. 5",
        "Companies Act Art. 69",
        "Commercial Code Art. 477",
        "Legal Notice 123 of 2025",
    ])
    status = random.choice(["discovered", "downloading", "processing", "indexed", "retrying"])  # noqa: S311
    return {
        "ts": _now_str(),
        "source": source["name"],
        "title": title,
        "reference": ref,
        "status": status,
    }


def run_startup_simulation() -> None:
    if st.session_state.get("demo_startup_done"):
        return

    with st.spinner("Initializing live legal monitoring demo..."):
        log = st.empty()

        # Header card with source list
        st.markdown(
            """
            <div style="background:#f8fafc;border:1px solid #e2e8f0;padding:14px;border-radius:10px;margin-bottom:10px;">
              <strong>Monitoring Sources</strong>: Legislation Malta • MFSA • Government Gazette • ROC (Malta Business Registry)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Step 1: probe sources
        p1 = st.progress(0, text="Checking sources: Legislation Malta, MFSA, Government Gazette, ROC")
        for i in range(0, 35, 5):
            time.sleep(0.12)
            p1.progress(i, text=f"Checking sources... {i}%")
            log.write(f"[{_now_str()}] discovery: probing sources...")

        # Step 2: discover publications and build a fake download queue
        p2 = st.progress(0, text="Discovering new publications")
        queue = _fake_download_queue(TARGET_FILE_COUNT)
        queue_ph = st.container()
        with queue_ph:
            st.markdown(f"<strong>Download queue</strong> <span style='color:#6b7280'>(showing first 12 of {len(queue)})</span>", unsafe_allow_html=True)
            preview = queue[:12]
            for item in preview:
                st.markdown(f"<div style='margin:4px 0'><code>{item['filename']}</code><br><span style='color:#6b7280;font-size:12px'>{item['source']} • {item['reference']}</span></div>", unsafe_allow_html=True)

        for i in range(0, 50, 10):
            time.sleep(0.12)
            p2.progress(i, text=f"Discovered {i//10 + 1} items")
            _append_event(generate_fake_update())

        # Step 3: simulate downloading many files with a rotating set of active bars
        st.markdown("<strong>Active downloads</strong>", unsafe_allow_html=True)
        bar_cols = st.columns(3)
        active_bars = [bar_cols[i % 3].progress(0, text="idle") for i in range(6)]
        completed = 0
        total_files = len(queue)
        per_step_sleep = 0.02
        steps_per_file = 5
        for idx, item in enumerate(queue):
            bar = active_bars[idx % len(active_bars)]
            for step in range(steps_per_file):
                time.sleep(per_step_sleep)
                # Simulate one retry occasionally
                if (idx % 47 == 0) and step == 2:
                    bar.progress(60, text="retrying...")
                    log.write(f"[{_now_str()}] download: timeout from {item['source']} – retrying {item['filename']}...")
                    time.sleep(per_step_sleep * 6)
                else:
                    pct = int(((step + 1) / steps_per_file) * 100)
                    bar.progress(pct, text=f"{item['filename'][:22]}... {pct}%")
            completed += 1
            if completed % 10 == 0:
                log.write(f"[{_now_str()}] downloaded {completed}/{total_files} files...")

        # Step 4: global processing + indexing
        p4 = st.progress(0, text="Processing: OCR/clean/segment")
        for i in range(0, 100, 25):
            time.sleep(0.14)
            p4.progress(i + 15, text=f"Processing... {i + 15}%")

        p5 = st.progress(0, text="Updating vector index")
        for i in range(0, 100, 25):
            time.sleep(0.12)
            p5.progress(i + 20, text=f"Indexing... {i + 20}%")

    st.session_state["demo_startup_done"] = True


def _append_event(event: Dict) -> None:
    events: List[Dict] = st.session_state.get("live_events", [])
    events.insert(0, event)
    st.session_state["live_events"] = events[:20]


def _fake_download_queue(n: int) -> List[Dict]:
    today = time.strftime("%Y-%m-%d")
    patterns = [
        ("Government Gazette", "Legal Notice {num} of 2025", "gazette_LN_{num}_2025_{slug}_{date}.pdf"),
        ("Legislation Malta", "S.L. 386.{minor:02d}", "sl_386_{minor:02d}_{slug}_{date}.pdf"),
        ("Legislation Malta", "Companies Act (Cap. 386)", "companies_act_cap386_{slug}_{date}.html"),
        ("MFSA", "MFSA Circular", "mfsa_circular_{slug}_{date}.pdf"),
        ("Malta Business Registry (ROC)", "ROC Practice Note", "roc_practice_note_{slug}_{date}.pdf"),
    ]
    out: List[Dict] = []
    for i in range(1, n + 1):
        src, ref_tmpl, file_tmpl = random.choice(patterns)
        slug = random.choice([
            "companies_act_fees", "annual_return_deadlines", "director_addresses",
            "beneficial_owners_register", "capital_requirements", "penalties_schedule"
        ])
        ref = ref_tmpl.format(num=100 + (i % 200), minor=1 + (i % 30))
        filename = file_tmpl.format(num=100 + (i % 200), minor=1 + (i % 30), slug=slug, date=today)
        out.append({
            "filename": filename,
            "source": src,
            "reference": ref,
        })
    return out


def maybe_emit_events(period_seconds: float = 6.0) -> None:
    last = st.session_state.get("live_last_emit", 0.0)
    now = time.time()
    if now - last < period_seconds:
        return
    # push 1-2 new events
    for _ in range(random.randint(1, 2)):
        _append_event(generate_fake_update())
    st.session_state["live_last_emit"] = now


def render_live_panel() -> None:
    # Fixed position panel top-left
    st.markdown(
        """
        <style>
        .live-panel { position: fixed; top: 1rem; left: 1rem; width: 360px; z-index: 9999; }
        .live-card { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; padding: 12px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.25); }
        .live-title { font-weight: 600; margin-bottom: 6px; }
        .live-item { border-left: 3px solid #1f77b4; padding: 6px 8px; margin: 6px 0; background: #161b22; border-radius: 6px; }
        .live-meta { font-size: 12px; color: #9da7b3; }
        .badge { background: #1f77b4; color: white; padding: 2px 6px; border-radius: 6px; font-size: 11px; margin-left: 6px; }
        </style>
        <div class="live-panel">
          <div class="live-card">
            <div class="live-title">Live Legal Monitor</div>
            <div id="live-items"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    items_html = []
    for ev in st.session_state.get("live_events", [])[:5]:
        badge = f"<span class='badge'>{ev['status']}</span>"
        items_html.append(
            f"<div class='live-item'><div class='live-meta'>{ev['ts']} — {ev['source']}{badge}</div><div><strong>{ev['reference']}</strong>: {ev['title']}</div></div>"
        )

    st.markdown(
        f"""
        <script>
          const el = window.parent.document.getElementById('live-items');
          if (el) {{ el.innerHTML = `{''.join(items_html)}`; }}
          setTimeout(() => {{ window.parent.dispatchEvent(new Event('liveTick')); }}, 10);
        </script>
        """,
        unsafe_allow_html=True,
    )


