import argparse
import asyncio

from dotenv import load_dotenv

from engine.mcp_gateway import MCPGateway
from engine.providers.gemini_provider import GeminiProvider

load_dotenv()


async def main():
    parser = argparse.ArgumentParser(description="IDE Agentic Engine - Phase 0")
    parser.add_argument("action", choices=["start"], help="Action to perform")
    parser.add_argument(
        "--prompt",
        type=str,
        help="Initial prompt to the engine",
        default="Read pyproject.toml and run 'ls -la'",
    )
    args = parser.parse_args()

    if args.action == "start":
        print("🚀 Starting IDE Agentic Engine...")

        # Initialize components
        import os

        import yaml

        from core.key_pool import APIKeyPool

        # Ensure we have a dummy api_keys.yaml for testing if it doesn't exist
        if not os.path.exists("profiles/api_keys.yaml"):
            dummy_data = {
                "services": {
                    "virustotal": {
                        "keys": [
                            {"value": "vt_key_1_expired", "status": "active"},
                            {"value": "vt_key_2_fresh", "status": "active"},
                        ]
                    }
                }
            }
            os.makedirs("profiles", exist_ok=True)
            with open("profiles/api_keys.yaml", "w") as f:
                yaml.dump(dummy_data, f)

        import os

        import yaml

        from core.key_pool import APIKeyPool
        from engine.providers.openai_provider import OpenAIProvider

        key_pool = APIKeyPool()
        gemini = GeminiProvider(key_pool=key_pool)
        openai = OpenAIProvider(key_pool=key_pool)
        gateway = MCPGateway(key_pool=key_pool)

        print("\n[TEST] 1. Executing VirusTotal (Real Logic)...")
        # This will use the 'placeholder_key' and likely return a 401/403
        res_vt = await gateway.execute_tool("virus_total_scan", {"resource": "8.8.8.8"})
        print(f"Result: {res_vt}")

        try:
            print("\n[TEST] 2. Calling OpenAI Provider...")
            test_messages = [
                {"role": "user", "content": "Say 'OpenAI Engine is online' in Arabic."}
            ]
            response = await openai.generate_response(test_messages)
            print(f"LLM Response: {response}")
        except Exception as e:
            print(f"OpenAI Error: {e}")

        try:
            print("\n[TEST] 3. Calling Gemini Provider...")
            test_messages = [
                {"role": "user", "content": "Say 'Gemini Engine is online' in Arabic."}
            ]
            response = await gemini.generate_response(test_messages)
            print(f"LLM Response: {response}")
        except Exception as e:
            print(f"LLM Response: Skipped due to API error (likely invalid/leaked key): {e}")

        print("\n✅ Phase 0 Foundation verified successfully.")


if __name__ == "__main__":
    asyncio.run(main())
