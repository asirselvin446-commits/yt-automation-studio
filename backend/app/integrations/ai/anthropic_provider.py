"""
Anthropic Claude AI Provider — Implements the AIProvider interface
using Anthropic's Messages API for video content analysis and
metadata generation.
"""
import json
import httpx
from typing import List, Dict, Any, Optional
from app.integrations.ai.base import (
    AIProvider, VideoAnalysisResult, GeneratedTitles,
    GeneratedDescription, GeneratedTags, GeneratedThumbnails
)
from app.core.logging import ai_logger


class AnthropicProvider(AIProvider):
    """AI provider using Anthropic Claude models."""

    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    async def _call_claude(self, prompt: str, system: str = "", max_tokens: int = 4096) -> Dict[str, Any]:
        """Call Anthropic Messages API expecting a JSON response."""
        if not self.api_key:
            ai_logger.warning("Anthropic API key not configured")
            return {}

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(self.BASE_URL, json=payload, headers=headers)
                if resp.status_code != 200:
                    ai_logger.error(f"Anthropic API error ({resp.status_code}): {resp.text}")
                    return {}

                data = resp.json()
                content_blocks = data.get("content", [])
                raw_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        raw_text += block.get("text", "")

                # Extract JSON from response (handle markdown code blocks)
                raw_text = raw_text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    # Remove first and last lines (```json and ```)
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    raw_text = "\n".join(lines)

                return json.loads(raw_text)

            except json.JSONDecodeError:
                ai_logger.error(f"Anthropic response is not valid JSON: {raw_text[:200]}")
                return {}
            except Exception as e:
                ai_logger.error(f"Anthropic API call failed: {e}")
                return {}

    async def analyze_content(self, transcript_or_text: str) -> VideoAnalysisResult:
        """Analyze video content from transcript."""
        system = (
            "You are an expert YouTube content analyst. Respond ONLY with pure JSON, "
            "no markdown formatting, no code blocks, no explanation."
        )
        prompt = f"""Analyze this video transcript or content overview.
Respond with JSON matching this exact structure:
{{
    "summary": "Clear 2-3 sentence overview of the video.",
    "topics": ["topic1", "topic2", "topic3"],
    "keywords": ["key1", "key2", "key3", "key4"],
    "target_audience": "Who this video is for",
    "content_category": "Category like Education, Entertainment, Tech, etc.",
    "key_moments": [
        {{"timestamp_label": "0:00", "description": "Introduction"}}
    ],
    "sentiment": "positive | neutral | negative",
    "estimated_engagement": "high | medium | low"
}}

TRANSCRIPT:
{transcript_or_text[:8000]}"""

        data = await self._call_claude(prompt, system)
        return VideoAnalysisResult(
            summary=data.get("summary", ""),
            topics=data.get("topics", []),
            keywords=data.get("keywords", []),
            target_audience=data.get("target_audience", ""),
            content_category=data.get("content_category", ""),
            key_moments=data.get("key_moments", []),
            sentiment=data.get("sentiment", "neutral"),
            estimated_engagement=data.get("estimated_engagement", "medium"),
        )

    async def generate_titles(self, transcript: str, channel_context: str = "") -> GeneratedTitles:
        """Generate 5 title candidates with reasoning."""
        system = (
            "You are a YouTube SEO and title optimization expert. "
            "Respond ONLY with pure JSON, no markdown, no code blocks."
        )
        prompt = f"""Generate exactly 5 YouTube title candidates for this video.
Each title must be unique, compelling, and optimized for click-through rate.
Keep titles under 100 characters. Include a mix of styles:
- 1 curiosity-driven title
- 1 direct/clear value title
- 1 emotional/power-word title
- 1 list/number title
- 1 question/how-to title

{f"Channel context: {channel_context}" if channel_context else ""}

Respond with JSON:
{{
    "titles": [
        {{
            "text": "The actual title text",
            "reasoning": "Why this title would work well",
            "style": "curiosity | value | emotional | list | question",
            "estimated_ctr_impact": "high | medium | low",
            "character_count": 45,
            "target_keywords": ["keyword1", "keyword2"]
        }}
    ]
}}

TRANSCRIPT:
{transcript[:6000]}"""

        data = await self._call_claude(prompt, system)
        return GeneratedTitles(titles=data.get("titles", []))

    async def generate_description(self, transcript: str, selected_title: str = "") -> GeneratedDescription:
        """Generate structured YouTube description."""
        system = (
            "You are a YouTube description writing expert. "
            "Respond ONLY with pure JSON, no markdown, no code blocks."
        )
        prompt = f"""Write a complete YouTube video description.
{f'Video title: "{selected_title}"' if selected_title else ''}

Include these sections:
1. Opening hook (first 2 lines visible before "Show more")
2. Detailed description (2-3 paragraphs)
3. Key timestamps/chapters
4. Call-to-action
5. Relevant hashtags (5-8)

Respond with JSON:
{{
    "short_description": "First 2 lines (hook, visible before fold)",
    "long_description": "Full detailed description with paragraphs",
    "chapters": [
        {{"timestamp": "0:00", "label": "Introduction"}},
        {{"timestamp": "1:30", "label": "Main Topic"}}
    ],
    "call_to_action": "Subscribe and hit the bell...",
    "hashtags": ["#topic1", "#topic2"],
    "link_placeholders": ["[Your Website]", "[Social Media]"]
}}

TRANSCRIPT:
{transcript[:6000]}"""

        data = await self._call_claude(prompt, system)
        return GeneratedDescription(
            short_description=data.get("short_description", ""),
            long_description=data.get("long_description", ""),
            chapters=data.get("chapters", []),
            call_to_action=data.get("call_to_action", ""),
            hashtags=data.get("hashtags", []),
            link_placeholders=data.get("link_placeholders", []),
        )

    async def generate_tags(self, transcript: str, title: str = "") -> GeneratedTags:
        """Generate classified YouTube tags."""
        system = (
            "You are a YouTube SEO tags expert. "
            "Respond ONLY with pure JSON, no markdown, no code blocks."
        )
        prompt = f"""Generate YouTube tags for this video.
{f'Title: "{title}"' if title else ''}

Classify tags into three categories:
- Primary (3-5): Broad topic tags
- Secondary (5-8): Specific topic tags
- Long-tail (5-8): Multi-word search phrases

Respond with JSON:
{{
    "primary_tags": ["tag1", "tag2"],
    "secondary_tags": ["specific tag1", "specific tag2"],
    "long_tail_tags": ["how to do something specific", "best way to learn X"],
    "total_character_count": 350,
    "search_intent": "informational | navigational | commercial | transactional"
}}

TRANSCRIPT:
{transcript[:4000]}"""

        data = await self._call_claude(prompt, system)
        return GeneratedTags(
            primary_tags=data.get("primary_tags", []),
            secondary_tags=data.get("secondary_tags", []),
            long_tail_tags=data.get("long_tail_tags", []),
            total_character_count=data.get("total_character_count", 0),
            search_intent=data.get("search_intent", "informational"),
        )

    async def generate_thumbnail_concepts(self, transcript: str, title: str = "") -> GeneratedThumbnails:
        """Generate thumbnail layout concepts."""
        system = (
            "You are a YouTube thumbnail design expert. "
            "Respond ONLY with pure JSON, no markdown, no code blocks."
        )
        prompt = f"""Design 3 thumbnail concepts for this video.
{f'Title: "{title}"' if title else ''}

Each concept should describe the visual layout for a 1280x720 thumbnail.

Respond with JSON:
{{
    "concepts": [
        {{
            "concept_name": "Concept A",
            "description": "Overall visual description",
            "text_overlay": "Bold text to display on thumbnail",
            "composition": "Rule of thirds, face close-up, split screen, etc.",
            "color_palette": ["#FF0000", "#FFFFFF", "#000000"],
            "emotion": "excitement | curiosity | shock | calm",
            "style": "minimalist | bold | cinematic | playful"
        }}
    ]
}}

TRANSCRIPT:
{transcript[:3000]}"""

        data = await self._call_claude(prompt, system)
        return GeneratedThumbnails(concepts=data.get("concepts", []))
