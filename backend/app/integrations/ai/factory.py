from typing import Optional
from app.core.config import settings
from app.integrations.ai.base import AIProvider
from app.integrations.ai.gemini_provider import GeminiProvider
from app.integrations.ai.openai_provider import OpenAIProvider
from app.integrations.ai.anthropic_provider import AnthropicProvider
from app.integrations.ai.local_provider import LocalAIProvider


class AIProviderFactory:
    """Dynamic AI provider selector based on user configuration."""

    PROVIDERS = {
        "gemini": lambda: GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL),
        "openai": lambda: OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL),
        "anthropic": lambda: AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL),
        "local": lambda: LocalAIProvider(base_url=settings.LOCAL_AI_BASE_URL, model=settings.LOCAL_AI_MODEL),
    }

    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> AIProvider:
        name = (provider_name or settings.DEFAULT_AI_PROVIDER).lower()

        if name == "openai" and settings.OPENAI_API_KEY:
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        elif name == "anthropic" and settings.ANTHROPIC_API_KEY:
            return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL)
        elif name == "local":
            return LocalAIProvider(base_url=settings.LOCAL_AI_BASE_URL, model=settings.LOCAL_AI_MODEL)
        else:
            # Default to GeminiProvider
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)

    @staticmethod
    def list_available() -> list:
        """Return list of provider names and their configuration status."""
        return [
            {"name": "gemini", "configured": bool(settings.GEMINI_API_KEY)},
            {"name": "openai", "configured": bool(settings.OPENAI_API_KEY)},
            {"name": "anthropic", "configured": bool(settings.ANTHROPIC_API_KEY)},
            {"name": "local", "configured": True},  # Local always available if server is running
        ]


ai_factory = AIProviderFactory()
