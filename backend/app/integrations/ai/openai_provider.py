import json
import httpx
from typing import List, Dict, Any, Optional
from app.integrations.ai.base import (
    AIProvider, VideoAnalysisResult, GeneratedTitles,
    GeneratedDescription, GeneratedTags, GeneratedThumbnails
)
from app.core.logging import ai_logger


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    async def _call_openai(self, prompt: str, system: str = "") -> Dict[str, Any]:
        if not self.api_key:
            return {}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code != 200:
                ai_logger.error(f"OpenAI error ({resp.status_code}): {resp.text}")
                return {}
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            try:
                return json.loads(content)
            except Exception:
                return {}

    async def analyze_content(self, transcript_or_text: str) -> VideoAnalysisResult:
        prompt = f"Analyze content and return JSON: summary, topics (list), keywords (list), entities, target_audience, content_category, important_moments. Content: {transcript_or_text[:8000]}"
        data = await self._call_openai(prompt, "You are a professional YouTube analyst.")
        return VideoAnalysisResult(
            summary=data.get("summary", "Video analyzed."),
            topics=data.get("topics", ["Tutorial", "Technology"]),
            keywords=data.get("keywords", ["video", "automation"]),
            entities=data.get("entities", []),
            target_audience=data.get("target_audience", "Tech-savvy creators"),
            content_category=data.get("content_category", "Education"),
            important_moments=data.get("important_moments", [])
        )

    async def generate_titles(self, summary: str, topics: List[str], count: int = 5) -> GeneratedTitles:
        prompt = f"Generate {count} YouTube title candidates with index, title, reasoning, intent, length. Summary: {summary}"
        data = await self._call_openai(prompt)
        titles = data.get("titles", [])
        return GeneratedTitles(titles=titles or [
            {"index": 1, "title": f"The Ultimate Guide to {topics[0] if topics else 'Video'}", "reasoning": "High search volume", "intent": "Search", "length": 45}
        ])

    async def generate_description(self, summary: str, transcript: str, chapters_info: Optional[List[Dict[str, Any]]] = None) -> GeneratedDescription:
        prompt = f"Generate YouTube description JSON with short_description, long_description, call_to_action, links_placeholder, hashtags, chapters. Summary: {summary}"
        data = await self._call_openai(prompt)
        return GeneratedDescription(
            short_description=data.get("short_description", summary[:120]),
            long_description=data.get("long_description", summary),
            call_to_action=data.get("call_to_action", "Subscribe for more content!"),
            links_placeholder=data.get("links_placeholder", "Links:\n- Website: https://..."),
            hashtags=data.get("hashtags", ["#YouTube", "#Tech"]),
            chapters=data.get("chapters", [{"timestamp": "00:00", "title": "Intro"}])
        )

    async def generate_tags(self, summary: str, topics: List[str]) -> GeneratedTags:
        prompt = f"Generate primary, secondary, long_tail keywords list for: {summary}"
        data = await self._call_openai(prompt)
        pri = data.get("primary_keywords", topics)
        sec = data.get("secondary_keywords", ["tips", "workflow"])
        lt = data.get("long_tail_keywords", ["how to automate youtube"])
        return GeneratedTags(
            primary_keywords=pri,
            secondary_keywords=sec,
            long_tail_keywords=lt,
            combined_tags_string=", ".join(pri + sec + lt)
        )

    async def generate_thumbnail_concepts(self, summary: str, selected_title: str) -> GeneratedThumbnails:
        prompt = f"Generate 3 thumbnail concepts for '{selected_title}'. Concepts: concept_title, text_suggestions, visual_composition, subject_placement, background_concept."
        data = await self._call_openai(prompt)
        return GeneratedThumbnails(concepts=data.get("concepts", []))

    async def generate_ideas(self, topic: str, niche: Optional[str], audience: Optional[str], count: int = 10) -> List[Dict[str, Any]]:
        prompt = f"Generate {count} YouTube video ideas with topic, title_concept, hook, video_structure, target_audience, production_difficulty for: {topic}"
        data = await self._call_openai(prompt)
        return data.get("ideas", [])

    async def analyze_channel_insights(self, query: str, channel_context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"Query: {query}. Distinguish data_basis, interpretation, actionable_suggestions (list). Channel context: {json.dumps(channel_context)}"
        return await self._call_openai(prompt)
