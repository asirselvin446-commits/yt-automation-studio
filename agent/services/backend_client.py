import httpx
from typing import Dict, Any, Optional
from app.core.logging import agent_logger


class AgentBackendClient:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url.rstrip("/")

    async def notify_new_video(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Register video with backend."""
        url = f"{self.backend_url}/api/v1/videos/internal-register"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return resp.json()
                agent_logger.error(f"Backend register error ({resp.status_code}): {resp.text}")
        except Exception as e:
            agent_logger.warning(f"Could not connect to Studio backend: {e}")
        return None
