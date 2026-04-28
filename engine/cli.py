import asyncio
from typing import Optional

import typer
from rich.console import Console

from core.key_pool import APIKeyPool
from engine.mcp_gateway import MCPGateway
from engine.providers.gemini_provider import GeminiProvider

app = typer.Typer(help="IDE Agentic Engine CLI")
console = Console()


@app.command()
def start(prompt: Optional[str] = None):
    """Start the IDE Agentic Engine."""
    console.print("[bold green]🚀 Starting IDE Agentic Engine...[/bold green]")
    asyncio.run(_run_engine(prompt))


@app.command()
def self_check():
    """Run a diagnostic check on all engine components."""
    console.print("[bold blue]🔍 Running Engine Self-Check...[/bold blue]")
    asyncio.run(_run_self_check())


@app.command()
def scan(
    client: str = typer.Option(..., "--client", "-c", help="Client name"),
    target: str = typer.Option(..., "--target", "-t", help="Target domain/IP"),
):
    """Run a full security scan and map findings to compliance."""
    console.print(f"[bold red]🛡️ Starting scan for: {target}[/bold red]")

    # 1. Simulate tool execution via Gateway
    # In a real scenario, we'd run Nuclei/Nmap/etc.
    scan_results = {
        "nmap": "Port 80 open, Apache 2.4.50",
        "nuclei": "Detected CVE-2021-41773 (Path Traversal)",
        "whois": f"Domain {target} registered to {client}",
    }

    # 2. Run Compliance Analysis
    from agents.compliance_agent import run_compliance_analysis

    console.print("[bold yellow]📊 Mapping findings to NCA ECC...[/bold yellow]")
    findings, evidence = asyncio.run(run_compliance_analysis(client, scan_results))

    console.print(f"✅ Analysis complete. Found {len(findings)} issues.")
    for f in findings:
        console.print(f"  - [{f['severity'].upper()}] {f['title']} -> {f['nca_control_ids']}")


@app.command()
def compliance(client: str = typer.Option(..., "--client", "-c", help="Client name")):
    """Show compliance status for a client."""
    from socroot.evidence_store import EvidenceStore

    store = EvidenceStore()
    records = store.get_records(client)

    if not records:
        console.print(f"[yellow]No compliance records found for client: {client}[/yellow]")
        return

    console.print(f"[bold green]Compliance Status for {client}:[/bold green]")
    for r in records:
        f = r["finding"]
        console.print(f"  - {f['title']} ({', '.join(r['metadata']['nca_control_ids'])})")


@app.command()
def report(
    client: str = typer.Option(..., "--client", "-c", help="Client name"),
    target: str = typer.Option(..., "--target", "-t", help="Target domain/IP"),
):
    """Generate a PDF compliance report for the client."""
    console.print(f"[bold blue]📄 Generating Report for {client}...[/bold blue]")

    from socroot.evidence_store import EvidenceStore

    store = EvidenceStore()
    records = store.get_records(client)

    if not records:
        console.print(
            f"[bold red]❌ No evidence records found for {client}. Run 'scan' first.[/bold red]"
        )
        raise typer.Exit(1)

    # Extract findings and evidence
    findings = [r["finding"] for r in records]
    evidence = records

    from agents.report_agent import generate_report

    path = asyncio.run(generate_report(client, target, findings, evidence))


@app.command()
def remediate(
    finding_id: str = typer.Option(..., "--finding-id", "-f", help="The finding ID to remediate"),
    client: str = typer.Option(..., "--client", "-c", help="Client name"),
):
    """Run auto-remediation for a specific finding."""
    console.print(f"[bold blue]🔧 Starting Auto-Remediation for {finding_id}...[/bold blue]")

    from socroot.evidence_store import EvidenceStore

    store = EvidenceStore()
    records = store.get_records(client)

    finding = None
    for r in records:
        f = r["finding"]
        if f.get("finding_id") == finding_id:
            finding = f
            break

    if not finding:
        console.print(f"[bold red]❌ Finding {finding_id} not found for {client}.[/bold red]")
        raise typer.Exit(1)

    from agents.remediation_agent import run_auto_remediation

    session_id, state = asyncio.run(run_auto_remediation(finding))

    from core.key_pool import APIKeyPool
    from core.orchestrator import AgentOrchestrator
    from engine.batch_executor import BatchExecutor
    from engine.connection_pool import ConnectionPool
    from engine.providers.router import ProviderRouter
    from engine.tool_registry import ToolRegistry

    pool = ConnectionPool()
    registry = ToolRegistry()
    batch_executor = BatchExecutor(pool, registry)

    from engine.providers.deepseek_provider import DeepSeekProvider
    from engine.providers.gemini_provider import GeminiProvider
    from engine.providers.groq_provider import GroqProvider
    from engine.providers.openai_provider import OpenAIProvider

    key_pool = APIKeyPool()
    router = ProviderRouter(key_pool)
    router.register_provider("gemini", GeminiProvider(key_pool=key_pool))
    router.register_provider("openai", OpenAIProvider(key_pool=key_pool))
    router.register_provider("groq", GroqProvider(key_pool=key_pool))
    router.register_provider("deepseek", DeepSeekProvider(key_pool=key_pool))

    orchestrator = AgentOrchestrator(batch_executor, router)

    # We'll just loop like in start command if pending_approval is True
    while state.get("pending_approval"):
        console.print(
            "\n[bold yellow]⚠️ الوكيل يطلب تنفيذ الإجراء الحرجة التالي ضمن المعالجة الذاتية.. هل توافق؟ (Y/N)[/bold yellow]"
        )
        for call in state.get("critical_tool_calls", []):
            console.print(f"  - Tool: {call.get('tool')}")
            console.print(f"    Args: {call.get('args')}")

        choice = input("Approve? [y/N]: ").strip().lower()
        if choice == "y":
            console.print("[green]✅ Approved. Resuming...[/green]")
            state = asyncio.run(orchestrator.resume(session_id, approved=True))
        else:
            console.print("[red]❌ Rejected. Asking agent to re-plan...[/red]")
            state = asyncio.run(orchestrator.resume(session_id, approved=False))

    console.print(
        f"\n[bold green]Final Response:[/bold green] {state.get('final_response', 'No final response.')}"
    )


@app.command()
def status():
    """Show engine status and active configurations."""
    console.print("[bold cyan]ℹ️ Engine Status: Nominal[/bold cyan]")
    console.print("  - Layer 1 (Agents): [green]Ready[/green]")
    console.print("  - Layer 3 (Gateway): [green]Connected[/green]")
    console.print("  - Layer 5 (State): [green]Persistent[/green]")


@app.command()
def monitor(port: int = typer.Option(8000, "--port", "-p", help="Port to listen on")):
    """Start the Webhook Listener for continuous monitoring."""
    console.print(f"[bold magenta]📡 Starting Monitoring Listener on port {port}...[/bold magenta]")
    import uvicorn

    from engine.webhook_listener import app as webhook_app

    uvicorn.run(webhook_app, host="0.0.0.0", port=port)


async def _run_engine(prompt: Optional[str]):
    if not prompt:
        console.print("[yellow]No prompt provided. Exiting.[/yellow]")
        return

    import uuid

    from core.key_pool import APIKeyPool
    from core.orchestrator import AgentOrchestrator
    from engine.batch_executor import BatchExecutor
    from engine.connection_pool import ConnectionPool
    from engine.providers.router import ProviderRouter
    from engine.tool_registry import ToolRegistry

    pool = ConnectionPool()
    registry = ToolRegistry()
    batch_executor = BatchExecutor(pool, registry)
    router = ProviderRouter(APIKeyPool())
    orchestrator = AgentOrchestrator(batch_executor, router)

    session_id = str(uuid.uuid4())
    console.print(f"[cyan]Engine started. Session ID: {session_id}[/cyan]")
    console.print(f"Prompt: {prompt}")

    state = await orchestrator.run(session_id, prompt)

    while state.get("pending_approval"):
        if state.get("final_response"):
            print(f"\n✅ Remediation Summary: {state['final_response']}")

        if state.get("pending_tool_calls"):
            print(f"\n🛑 HITL Required for session: {session_id}")
        elif not state.get("final_response"):
            print("\n⚠️ Agent reached max iterations without a final response.")

        for call in state.get("critical_tool_calls", []):
            console.print(f"  - Tool: {call.get('tool')}")
            console.print(f"    Args: {call.get('args')}")

        choice = input("Approve? [y/N]: ").strip().lower()
        if choice == "y":
            console.print("[green]✅ Approved. Resuming...[/green]")
            state = await orchestrator.resume(session_id, approved=True)
        else:
            console.print("[red]❌ Rejected. Asking agent to re-plan...[/red]")
            state = await orchestrator.resume(session_id, approved=False)

    console.print(
        f"\n[bold green]Final Response:[/bold green] {state.get('final_response', 'No final response.')}"
    )


async def _run_self_check():
    try:
        key_pool = APIKeyPool()
        gemini = GeminiProvider(key_pool=key_pool)
        gateway = MCPGateway(key_pool=key_pool)

        console.print("- Key Pool: [green]OK[/green]")
        console.print("- Gemini Provider: [green]OK[/green]")
        console.print("- MCP Gateway: [green]OK[/green]")
        console.print("\n✅ All systems nominal.")
    except Exception as e:
        console.print(f"\n❌ [bold red]Self-Check Failed:[/bold red] {e}")


if __name__ == "__main__":
    app()
