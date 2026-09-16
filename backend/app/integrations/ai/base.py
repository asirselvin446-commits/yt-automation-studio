from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class GeneratedTitles(BaseModel):
    titles: List[Dict[str, Any]]  # [{ "index": 1, "title": "...", "reasoning": "...", "intent": "...", "length": 52 }]


class GeneratedDescription(BaseModel):
    short_description: str
    long_description: str
    call_to_action: str
    links_placeholder: str
    hashtags: List[str]
    chapters: List[Dict[str, Any]]


class GeneratedTags(BaseModel):
    primary_keywords: List[str]
    secondary_keywords: List[str]
    long_tail_keywords: List[str]
    combined_tags_string: str


class GeneratedThumbnails(BaseModel):
    concepts: List[Dict[str, Any]]  # [{ "concept_title": "...", "text_suggestions": "...", "visual_composition": "...", "subject_placement": "...", "background_concept": "..." }]


class VideoAnalysisResult(BaseModel):
    summary: str
    topics: List[str]
    keywords: List[str]
    entities: List[Dict[str, Any]]
    target_audience: str
    content_category: str
    important_moments: List[Dict[str, Any]]


class AIProvider(ABC):
    """Abstract base provider for LLM engines."""

    @abstractmethod
    async def analyze_content(self, transcript_or_text: str) -> VideoAnalysisResult:
        """Perform deep content classification and summary from video transcript."""
        pass

    @abstractmethod
    async def generate_titles(self, summary: str, topics: List[str], count: int = 5) -> GeneratedTitles:
        """Generate 5 title candidates with reasoning, intent, and length."""
        pass

    @abstractmethod
    async def generate_description(self, summary: str, transcript: str, chapters_info: Optional[List[Dict[str, Any]]] = None) -> GeneratedDescription:
        """Generate structured YouTube description without inventing false facts."""
        pass

    @abstractmethod
    async def generate_tags(self, summary: str, topics: List[str]) -> GeneratedTags:
        """Generate primary, secondary, and long-tail YouTube tags."""
        pass

    @abstractmethod
    async def generate_thumbnail_concepts(self, summary: str, selected_title: str) -> GeneratedThumbnails:
        """Generate thumbnail visual composition concepts."""
        pass

    @abstractmethod
    async def generate_ideas(self, topic: str, niche: Optional[str], audience: Optional[str], count: int = 10) -> List[Dict[str, Any]]:
        """Generate 10 actionable video ideas with hooks and outlines."""
        pass

    @abstractmethod
    async def analyze_channel_insights(self, query: str, channel_context: Dict[str, Any]) -> Dict[str, Any]:
        """Channel Brain analysis separating DATA from INTERPRETATION from SUGGESTION."""
        pass
