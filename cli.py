import argparse
from rich.console import Console
from rich.panel import Panel
from engine.agent_orchestrator import AgentOrchestrator
from engine.workspace_context import WorkspaceContext

console = Console()

def main():
    parser = argparse.ArgumentParser(description="IDE Agent Engine CLI")
    parser.add_argument("--prompt", required=True, help="The task or instruction for the agent")
    
    args = parser.parse_args()
    
    console.print(Panel(f"[bold blue]IDE Agent Engine Initialized[/bold blue]\n[green]Task:[/green] {args.prompt}"))
    
    # Initialize workspace context (e.g., reading .cursorrules)
    context = WorkspaceContext()
    system_prompt = context.get_system_prompt()
    
    # In a fully realized system, the orchestrator would take the system_prompt
    orchestrator = AgentOrchestrator()
    
    try:
        orchestrator.run(args.prompt)
    except Exception as e:
        console.print(f"[bold red]Engine Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
