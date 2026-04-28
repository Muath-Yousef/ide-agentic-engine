import asyncio
import sys
import os

# Add workspace root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from packages.shared_mcps.servers.socroot_state_server import mcp as state_mcp
from packages.shared_mcps.servers.socroot_evidence_chain import mcp as evidence_mcp
from packages.shared_mcps.servers.socroot_development import mcp as dev_mcp

async def test_mcps():
    print("Testing MCP Servers Initialization...")
    
    # 1. Test State MCP
    state_tools = state_mcp.list_tools()
    print(f"[OK] State Server loaded. Tools: {[t.name for t in state_tools]}")
    
    # 2. Test Evidence MCP
    evidence_tools = evidence_mcp.list_tools()
    print(f"[OK] Evidence Server loaded. Tools: {[t.name for t in evidence_tools]}")
    
    # 3. Test Dev MCP
    dev_tools = dev_mcp.list_tools()
    print(f"[OK] Dev Server loaded. Tools: {[t.name for t in dev_tools]}")
    
    print("All shared MCP servers are successfully loaded and ready for integration!")

if __name__ == "__main__":
    asyncio.run(test_mcps())
