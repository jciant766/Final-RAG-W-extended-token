#!/usr/bin/env python3
"""
Rich-based terminal demo: Malta legal document monitoring dashboard

Run:
  python rich_monitor_demo.py

Deps:
  pip install rich
"""

import itertools
import random
import time
from datetime import datetime
from typing import Deque, Dict, List, Tuple
from collections import deque

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


console = Console()


SOURCES: List[Dict[str, List[str]]] = [
    {
        "name": "Legislation Malta",
        "items": [
            "Commercial Code (Cap. 13) – Art. 477 update",
            "Companies Act (Cap. 386) – consolidation",
            "Subsidiary Legislation 386.{minor:02d} – revision",
        ],
    },
    {
        "name": "MFSA",
        "items": [
            "MFSA Circular – Annual return deadlines",
            "MFSA Guidance – Beneficial Ownership Register",
            "MFSA Notice – Prospectus Rules update",
        ],
    },
    {
        "name": "Government Gazette",
        "items": [
            "Legal Notice {num} of 2025 – Companies Act (Fees) Regs",
            "Legal Notice {num} of 2025 – S.L. 386.{minor:02d} update",
        ],
    },
    {
        "name": "ROC (Malta Business Registry)",
        "items": [
            "ROC Practice Note – Director address disclosures",
            "ROC e-Filing spec – schema update",
        ],
    },
]


Doc = Dict[str, str]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fake_ref() -> Tuple[str, str, str]:
    src = random.choice(SOURCES)
    tmpl = random.choice(src["items"])
    ref = tmpl.format(num=random.randint(100, 299), minor=random.randint(1, 30))
    # Generate a plausible file name
    slug = random.choice(
        [
            "companies_act_fees",
            "annual_return_deadlines",
            "director_addresses",
            "beneficial_owners_register",
            "capital_requirements",
            "penalties_schedule",
        ]
    )
    fname = f"{src['name'].split()[0].lower()}_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return src["name"], ref, fname


def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=1),
    )
    layout["body"].split_row(
        Layout(name="sidebar", size=38),
        Layout(name="main", ratio=1),
    )
    layout["main"].split(Layout(name="summary", size=7), Layout(name="tables"))
    return layout


def header() -> Panel:
    title = Text("Malta Legal Monitoring", style="bold white on dark_green")
    subtitle = Text(f" Live demo • {now_str()} ", style="dim")
    content = Align.center(Group(title, subtitle))
    return Panel(content, style="bold", box=box.ROUNDED)


def footer(installed: int, total: int) -> Panel:
    pct = int(installed * 100 / max(1, total))
    return Panel(Text(f"Installed {installed}/{total} documents • {pct}%", justify="center"), box=box.SIMPLE)


def sources_panel(status: Dict[str, str]) -> Panel:
    tbl = Table.grid(padding=(0, 1))
    for src, state in status.items():
        mark = "[green]●[/]" if state == "OK" else "[yellow]●[/]" if state == "SYNC" else "[red]●[/]"
        tbl.add_row(mark, Text(src, style="bold"), Text(state, style="dim"))
    return Panel(tbl, title="Sources", box=box.ROUNDED, border_style="cyan")


def progress_group() -> Progress:
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold]Task[/]"),
        BarColumn(bar_width=None),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        expand=True,
    )


def docs_table(rows: List[Doc]) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Time", width=8)
    table.add_column("Source", min_width=16)
    table.add_column("Reference", min_width=32)
    table.add_column("File", min_width=24)
    for r in rows:
        table.add_row(r["time"].split()[1], r["source"], r["reference"], r["file"])
    return Panel(table, title="Recent Publications", border_style="magenta")


def log_panel(lines: Deque[str]) -> Panel:
    content = "\n".join(list(lines)[-12:])
    return Panel(Text(content), title="Activity Log", border_style="yellow", box=box.ROUNDED)


def main(runtime_seconds: int = 60, total_install: int = 300) -> None:
    layout = make_layout()

    # Source status
    status = {
        "Legislation Malta": "SYNC",
        "MFSA": "OK",
        "Government Gazette": "OK",
        "ROC (Malta Business Registry)": "OK",
    }

    # Rolling data
    recent_docs: List[Doc] = []
    logs: Deque[str] = deque(maxlen=200)

    # Progress bars
    p = progress_group()
    disc = p.add_task("Discovery", total=100)
    down = p.add_task("Downloading", total=total_install)
    proc = p.add_task("Processing", total=total_install)
    index = p.add_task("Indexing", total=total_install)

    installed = 0
    ticks = 0
    next_source_flip = 0

    with Live(layout, refresh_per_second=10, console=console):
        start = time.time()
        while time.time() - start < runtime_seconds:
            ticks += 1

            # Occasionally flip sync status for realism
            if ticks >= next_source_flip:
                status["Legislation Malta"] = random.choice(["OK", "SYNC"])
                next_source_flip = ticks + random.randint(20, 40)

            # Simulate discovery pulse
            p.advance(disc, random.randint(3, 8))
            if p.tasks[disc].completed >= 100:
                p.reset(disc)

            # Generate new docs intermittently
            for _ in range(random.randint(1, 3)):
                source, reference, fname = fake_ref()
                new_doc = {"time": now_str(), "source": source, "reference": reference, "file": fname}
                recent_docs.insert(0, new_doc)
                recent_docs[:] = recent_docs[:10]
                logs.appendleft(f"{new_doc['time']}  discovered  {reference} [{source}] → {fname}")

            # Advance pipeline
            advance_download = random.randint(1, 4)
            advance_process = random.randint(1, 5)
            advance_index = random.randint(1, 6)
            p.advance(down, advance_download)
            p.advance(proc, advance_process)
            p.advance(index, advance_index)

            installed = min(total_install, int(p.tasks[index].completed))

            # Update panels
            layout["header"].update(header())
            layout["sidebar"].update(sources_panel(status))
            layout["summary"].update(Panel(p, title="Pipeline", border_style="green", box=box.ROUNDED))
            layout["tables"].update(Group(docs_table(recent_docs), Rule(), log_panel(logs)))
            layout["footer"].update(footer(installed, total_install))

            time.sleep(0.12)

    console.print("\n[bold green]Demo finished.[/] Press Ctrl+C to exit or re-run for another session.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user.[/]")



