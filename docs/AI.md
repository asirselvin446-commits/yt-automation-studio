# YT Automation Studio — AI Engine

## Overview

The AI engine uses a **provider abstraction pattern** to support multiple AI services. All providers implement the same interface (`AIProvider` base class), making it seamless to switch between them.

## Supported Providers

| Provider | Model | Best For | Cost |
|:---|:---|:---|:---|
| **Google Gemini** | `gemini-1.5-flash` / `pro` | Default, fast, cost-effective | Low |
| **OpenAI** | `gpt-4o` | Premium quality | Medium |
| **Anthropic Claude** | `claude-3-5-sonnet` | Detailed analysis, long context | Medium |
| **Local (Ollama)** | `llama3:8b` | Free, offline, privacy | Free |

## Configuration

Set your preferred provider and API key in `.env`:
```env
DEFAULT_AI_PROVIDER=gemini    # gemini | openai | anthropic | local
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
LOCAL_AI_BASE_URL=http://localhost:11434/v1
LOCAL_AI_MODEL=llama3:8b
```

## AI Pipeline

Each video goes through a 5-step AI analysis pipeline:

### 1. Content Analysis
- Input: Video transcript or content description
- Output: Summary, topics, keywords, target audience, content category, sentiment

### 2. Title Generation (5 candidates)
- Generates 5 unique title candidates with different styles:
  - **Curiosity-driven** — "You Won't Believe What Happens When..."
  - **Direct value** — "Complete Guide to React Hooks in 2024"
  - **Emotional/power-word** — "The Life-Changing Habit Nobody Talks About"
  - **List/number** — "7 Mistakes Every Beginner Makes"
  - **Question/how-to** — "How to Build a SaaS in 30 Days?"
- Each candidate includes: reasoning, style, estimated CTR impact, character count

### 3. Description Generation
- **Short description**: First 2 lines (visible before "Show more")
- **Long description**: Full detailed paragraphs
- **Chapters**: Timestamped sections for video navigation
- **Call-to-action**: Subscribe prompt
- **Hashtags**: 5-8 relevant tags

### 4. Tag Classification
- **Primary tags** (3-5): Broad topic tags
- **Secondary tags** (5-8): Specific topic tags
- **Long-tail tags** (5-8): Multi-word search phrases
- **Search intent**: informational / navigational / commercial / transactional

### 5. Thumbnail Concepts
- 3 concept designs per video
- Each includes: description, text overlay, composition, color palette, emotion, style

## Versioned Metadata

Every AI generation is versioned (`v1`, `v2`, `v3`...) with full provenance:
- Provider name and model used
- Prompt version
- Tokens consumed
- Estimated cost
- Timestamp

Users can regenerate metadata at any time, and all previous versions are preserved.

## Quality Presets

| Preset | Description |
|:---|:---|
| `low_cost` | Faster models, shorter prompts, fewer tokens |
| `balanced` | Default balance of quality and cost |
| `high_quality` | Best models, detailed prompts, maximum tokens |

## Adding a New Provider

1. Create `backend/app/integrations/ai/new_provider.py`
2. Extend the `AIProvider` base class
3. Implement all 5 abstract methods
4. Register in `factory.py`
5. Add configuration to `config.py` and `.env.example`
