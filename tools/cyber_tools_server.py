from typing import Any, Dict, Optional

import httpx


async def virustotal_scan(resource: str, api_key: str) -> str:
    """
    Perform a VirusTotal reputation check for an IP, domain, or file hash.
    """
    url = f"https://www.virustotal.com/api/v3/search?query={resource}"
    headers = {"x-apikey": api_key}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)

            if response.status_code == 429:
                raise Exception("429 Rate Limit Exceeded")
            if response.status_code == 403 or response.status_code == 401:
                raise Exception("403 Forbidden - Quota Exceeded or Invalid Key")

            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                return f"No results found for {resource}."

            # Parse results from search endpoint
            attributes = data["data"][0].get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)

            return f"VirusTotal Results for {resource}:\n- Malicious: {malicious}\n- Suspicious: {suspicious}\n- Analysis: {'🚨 MALICIOUS' if malicious > 0 else '✅ CLEAN'}"

        except httpx.HTTPStatusError as e:
            return f"VirusTotal API Status Error: {e}"
        except httpx.RequestError as e:
            return f"VirusTotal Request Error: {e}"
        except Exception as e:
            # Propagate for rotation
            raise e
