import asyncio
import os
import sys
import json

# Add packages to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(root_dir, "ide-engine"))
sys.path.append(os.path.join(root_dir, "shared_mcps"))

async def test_monorepo_integration():
    print("=== [TEST 1] Monorepo Structure & Environment ===")
    packages = ["ide-engine", "soc-core", "shared_mcps", "shared_skills"]
    for pkg in packages:
        path = os.path.join(root_dir, pkg)
        if os.path.exists(path):
            print(f"[OK] Package {pkg} found at {path}")
        else:
            print(f"[FAIL] Package {pkg} MISSING at {path}")

    print("\n=== [TEST 2] Skill Loading in AgentOrchestrator ===")
    try:
        from core.orchestrator import AgentOrchestrator
        from engine.batch_executor import BatchExecutor
        from engine.providers.router import ProviderRouter
        
        # Mock dependencies
        executor = BatchExecutor(connection_pool=None, tool_registry=None)
        router = ProviderRouter()
        
        orchestrator = AgentOrchestrator(batch_executor=executor, router=router)
        
        if orchestrator.skills_content:
            print(f"[OK] AgentOrchestrator successfully loaded skills.")
            print(f"DEBUG: Found Skills:\n{orchestrator.skills_content[:200]}...")
        else:
            print(f"[FAIL] AgentOrchestrator skills_content is empty.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize AgentOrchestrator: {e}")

    print("\n=== [TEST 3] Shared MCP Servers Tools ===")
    try:
        from shared_mcps.servers.socroot_state_server import mcp as state_mcp
        from shared_mcps.servers.socroot_evidence_chain import mcp as evidence_mcp
        
        state_tools = [t.name for t in state_mcp.list_tools()]
        evidence_tools = [t.name for t in evidence_mcp.list_tools()]
        
        print(f"[OK] State MCP Tools: {state_tools}")
        print(f"[OK] Evidence MCP Tools: {evidence_tools}")
    except Exception as e:
        print(f"[ERROR] Failed to load MCP tools: {e}")

if __name__ == "__main__":
    asyncio.run(test_monorepo_integration())
