# AI Layer & Provider Abstraction

## 1. Provider Abstraction Architecture
YT Automation Studio avoids vendor lock-in by decoupling business logic from LLM APIs via `AIProvider`:

```
          AIProvider (Abstract Interface)
                         │
      ┌──────────┬───────┴────────┬─────────────┐
      ▼          ▼                ▼             ▼
GeminiProvider  OpenAIProvider  AnthropicProvider  LocalAIProvider
```

### Supported Providers
1. **Google Gemini**: Default high-speed, cost-effective multimodal provider (`gemini-1.5-flash` / `pro`).
2. **OpenAI**: `gpt-4o` with JSON schema enforcement.
3. **Anthropic Claude**: `claude-3-5-sonnet` for advanced analytical synthesis.
4. **Local AI**: Connects to local Ollama, vLLM, or LocalAI instances via standard OpenAI-compatible endpoints (`http://localhost:11434/v1`).

---

## 2. Core Capabilities
- **Content Classification**: Analyzes video transcript and extracts summary, topics, keywords, target audience, and key moments.
- **5 Title Candidates**: Evaluates 5 distinct psychological angles (intrigue, search, how-to, value-first, question) without making false guarantees about CTR.
- **Description & Chapters**: Formats structured long description, call to action, and timestamped chapters strictly based on verified media content.
- **SEO Tags**: Classifies keywords into Primary, Secondary, and Long-Tail tags to avoid keyword stuffing.
- **Thumbnail Concepts**: Generates layout composition, subject placement, and text overlay ideas.
- **Channel Brain Q&A**: Answers creator questions while strictly segregating:
  - `DATA` (pure numerical facts)
  - `INTERPRETATION` (logical deductions)
  - `SUGGESTION` (actionable next steps)
