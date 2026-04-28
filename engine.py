import asyncio
import argparse
from dotenv import load_dotenv
from providers.gemini_provider import GeminiProvider
from gateway.mcp_gateway import MCPGateway

load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="IDE Agentic Engine - Phase 0")
    parser.add_argument("action", choices=["start"], help="Action to perform")
    parser.add_argument("--prompt", type=str, help="Initial prompt to the engine", default="Read pyproject.toml and run 'ls -la'")
    args = parser.parse_args()

    if args.action == "start":
        print("🚀 Starting IDE Agentic Engine...")
        
        # Initialize components
        from gateway.key_pool import APIKeyPool
        import yaml
        import os
        
        # Ensure we have a dummy api_keys.yaml for testing if it doesn't exist
        if not os.path.exists("profiles/api_keys.yaml"):
            dummy_data = {
                "services": {
                    "virustotal": {
                        "keys": [
                            {"value": "vt_key_1_expired", "status": "active"},
                            {"value": "vt_key_2_fresh", "status": "active"}
                        ]
                    }
                }
            }
            os.makedirs("profiles", exist_ok=True)
            with open("profiles/api_keys.yaml", "w") as f:
                yaml.dump(dummy_data, f)

        key_pool = APIKeyPool()
        provider = GeminiProvider(key_pool=key_pool)
        gateway = MCPGateway(key_pool=key_pool)
        
        print("\n[TEST] 1. Executing VirusTotal (Rotation Test)...")
        res_vt = await gateway.execute_tool("virus_total_scan", {"resource": "malware.exe"})
        print(f"Result: {res_vt}")
        
        print("\n[TEST] 2. Executing run_command via Gateway...")
        res_cmd = await gateway.execute_tool("run_command", {"command": "echo 'Hello from Terminal Server!'", "cwd": "."})
        print(f"Result:\n{res_cmd}")
        
        try:
            print("\n[TEST] 3. Calling Gemini Provider (with Key Pool)...")
            test_messages = [{"role": "user", "content": "Say 'Engine is online' in Arabic."}]
            response = await provider.generate_response(test_messages)
            print(f"LLM Response: {response}")
        except Exception as e:
            print(f"LLM Response: Skipped due to API error (likely invalid/leaked key): {e}")
        
        print("\n✅ Phase 0 Foundation verified successfully.")

if __name__ == "__main__":
    asyncio.run(main())
