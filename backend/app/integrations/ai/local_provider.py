import json
import httpx
from typing import List, Dict, Any, Optional
from app.integrations.ai.base import (
    AIProvider, VideoAnalysisResult, GeneratedTitles,
    GeneratedDescription, GeneratedTags, GeneratedThumbnails
)
from app.core.logging import ai_logger


class LocalAIProvider(AIProvider):
    """Local LLM provider connecting to Ollama, LM Studio, vLLM, or LocalAI."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3:8b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def _call_local(self, prompt: str, system: str = "") -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or "You are a YouTube assistant. Output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    return json.loads(content)
        except Exception as e:
            ai_logger.warning(f"Local AI endpoint unreachable ({self.base_url}): {e}")
        return {}

    async def analyze_content(self, transcript_or_text: str) -> VideoAnalysisResult:
        data = await self._call_local(f"Analyze: {transcript_or_text[:5000]}")
        return VideoAnalysisResult(
            summary=data.get("summary", "Local analysis performed."),
            topics=data.get("topics", ["Tutorial"]),
            keywords=data.get("keywords", ["video"]),
            entities=data.get("entities", []),
            target_audience=data.get("target_audience", "General audience"),
            content_category=data.get("content_category", "Education"),
            important_moments=data.get("important_moments", [])
        )

    async def generate_titles(self, summary: str, topics: List[str], count: int = 5) -> GeneratedTitles:
        data = await self._call_local(f"Generate {count} titles for: {summary}")
        return GeneratedTitles(titles=data.get("titles", []))

    async def generate_description(self, summary: str, transcript: str, chapters_info: Optional[List[Dict[str, Any]]] = None) -> GeneratedDescription:
        data = await self._call_local(f"Generate description for: {summary}")
        return GeneratedDescription(
            short_description=data.get("short_description", summary[:100]),
            long_description=data.get("long_description", summary),
            call_to_action=data.get("call_to_action", "Subscribe!"),
            links_placeholder=data.get("links_placeholder", "Links: ..."),
            hashtags=data.get("hashtags", ["#Video"]),
            chapters=data.get("chapters", [])
        )

    async def generate_tags(self, summary: str, topics: List[str]) -> GeneratedTags:
        data = await self._call_local(f"Generate tags for: {summary}")
        return GeneratedTags(
            primary_keywords=data.get("primary_keywords", topics),
            secondary_keywords=data.get("secondary_keywords", []),
            long_tail_keywords=data.get("long_tail_keywords", []),
            combined_tags_string=", ".join(topics)
        )

    async def generate_thumbnail_concepts(self, summary: str, selected_title: str) -> GeneratedThumbnails:
        data = await self._call_local(f"Thumbnail concepts for: {selected_title}")
        return GeneratedThumbnails(concepts=data.get("concepts", []))

    async def generate_ideas(self, topic: str, niche: Optional[str], audience: Optional[str], count: int = 10) -> List[Dict[str, Any]]:
        data = await self._call_local(f"Ideas for topic: {topic}")
        return data.get("ideas", [])

    async def analyze_channel_insights(self, query: str, channel_context: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_local(f"Analyze channel query: {query}")
