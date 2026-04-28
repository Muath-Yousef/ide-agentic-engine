"""
CLI entry point — one command to rule them all.

Usage::

    ide-agent scan   --client asasEdu --target asas4edu.net
    ide-agent compliance --client asasEdu
    ide-agent status
    ide-agent self-check
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from engine import __version__

app = typer.Typer(
    name="ide-agent",
    help="ide-agentic-engine v2 — CLI Agentic Engine for IDE AI workflows.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True, style="bold red")

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def scan(
    client: Annotated[str, typer.Option("--client", "-c", help="Client ID")],
    target: Annotated[str, typer.Option("--target", "-t", help="Target domain or IP")],
    report_type: Annotated[
        str, typer.Option("--report-type", "-r", help="both | executive | technical")
    ] = "both",
    session_id: Annotated[
        str | None, typer.Option("--session", "-s", help="Resume existing session")
    ] = None,
) -> None:
    """Run a full cybersecurity scan for a client and generate a compliance report."""
    _configure_logging()
    console.print(Panel(f"[bold cyan]Scanning:[/] {target}  |  Client: {client}", title="ide-agent"))
    asyncio.run(_run_scan(client, target, report_type, session_id))


@app.command()
def compliance(
    client: Annotated[str, typer.Option("--client", "-c", help="Client ID")],
    results_file: Annotated[
        str | None,
        typer.Option("--results", "-r", help="Path to existing scan results JSON")
    ] = None,
) -> None:
    """Map existing scan results to NCA ECC controls and generate evidence records."""
    _configure_logging()
    asyncio.run(_run_compliance(client, results_file))


@app.command(name="self-check")
def self_check_cmd() -> None:
    """Validate environment variables, packages, and Redis connectivity."""
    from engine import self_check
    try:
        self_check()
    except SystemExit:
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show engine configuration and connectivity status."""
    import os
    _configure_logging(quiet=True)

    table = Table(title=f"ide-agentic-engine v{__version__} — Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Value")

    redis_url = os.environ.get("REDIS_URL", "not set")
    table.add_row("Redis URL", "✓" if redis_url != "not set" else "✗", redis_url)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    table.add_row(
        "Anthropic API Key",
        "✓" if api_key else "✗",
        f"...{api_key[-6:]}" if api_key else "missing",
    )

    sonnet = os.environ.get("SONNET_MODEL", "claude-sonnet-4-6")
    haiku = os.environ.get("HAIKU_MODEL", "claude-haiku-4-5-20251001")
    table.add_row("Sonnet model", "✓", sonnet)
    table.add_row("Haiku model", "✓", haiku)

    console.print(table)


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _run_scan(
    client: str,
    target: str,
    report_type: str,
    session_id: str | None,
) -> None:
    from engine.orchestrator import AgentState, create_graph
    from engine.session_store import SessionStore

    store = SessionStore()
    sid = session_id or store.new_session_id()

    # Resume or create state
    state: AgentState | None = await store.load(sid) if session_id else None
    if state is None:
        state = AgentState(
            client_id=client,
            target=target,
            task_type="compliance",
            task_description=f"Full cybersecurity scan for {target} — report type: {report_type}",
            messages=[],
            batch_results=[],
            compliance_findings=[],
            evidence_records=[],
            scan_results={},
            final_report_path="",
            error="",
            iteration_count=0,
        )

    graph = create_graph()

    with console.status("[bold green]Running agentic workflow..."):
        result: AgentState = await graph.ainvoke(state)  # type: ignore[assignment]

    await store.save(sid, dict(result))

    if result.get("error"):
        err_console.print(f"[ERROR] {result['error']}")
        raise typer.Exit(1)

    report_path = result.get("final_report_path", "")
    findings_count = len(result.get("compliance_findings", []))

    console.print(Panel(
        f"[bold green]✓ Scan complete[/]\n"
        f"Session: {sid}\n"
        f"Findings: {findings_count}\n"
        f"Report: {report_path or 'N/A'}",
        title="Results",
    ))


async def _run_compliance(client: str, results_file: str | None) -> None:
    import json as _json

    scan_results: dict = {}
    if results_file:
        try:
            with open(results_file, "r", encoding="utf-8") as fh:
                scan_results = _json.load(fh)
        except (OSError, ValueError) as exc:
            err_console.print(f"Cannot read results file: {exc}")
            raise typer.Exit(1)

    from agents.compliance_agent import run_compliance_analysis

    with console.status("[bold green]Mapping to NCA ECC controls..."):
        findings, evidence = await run_compliance_analysis(client, scan_results)

    console.print(
        Panel(
            f"[bold green]✓ Compliance analysis complete[/]\n"
            f"Findings: {len(findings)}\n"
            f"Evidence records: {len(evidence)}",
            title="Compliance",
        )
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_logging(quiet: bool = False) -> None:
    level = logging.WARNING if quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy third-party loggers
    for noisy in ("httpx", "anthropic", "opentelemetry"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


if __name__ == "__main__":
    app()
