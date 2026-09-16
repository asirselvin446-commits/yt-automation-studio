from typing import Optional
from app.core.config import settings
from app.integrations.ai.base import AIProvider
from app.integrations.ai.gemini_provider import GeminiProvider
from app.integrations.ai.openai_provider import OpenAIProvider
from app.integrations.ai.local_provider import LocalAIProvider


class AIProviderFactory:
    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> AIProvider:
        name = (provider_name or settings.DEFAULT_AI_PROVIDER).lower()

        if name == "openai" and settings.OPENAI_API_KEY:
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        elif name == "local":
            return LocalAIProvider(base_url=settings.LOCAL_AI_BASE_URL, model=settings.LOCAL_AI_MODEL)
        else:
            # Default to GeminiProvider (with internal graceful heuristics if API key is not yet set)
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


ai_factory = AIProviderFactory()
