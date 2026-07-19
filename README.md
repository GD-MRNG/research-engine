# research-engine

A specialised workflow engine for web research pipelines that produce blog posts. Extracted from [cognitive-engine](../README.md) to enable independent development of the research and publishing stack.

Each pipeline: **source CSV → web scrape → LLM extraction → synthesis → Jinja2 report → S3 archive + Jekyll publish + Discord notification**

## Setup

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/), Firefox (for Selenium), Ollama (for local models)

```bash
# Clone this repo and the cognitive-assets repo
git clone <this-repo> research-engine
cd research-engine
git clone <cognitive-assets-repo> cognitive-assets

# Install dependencies
uv sync

# Copy and fill in API keys
cp .env.example .env
```

**.env keys required:**
```
POE_API_KEY=
YOUTUBE_TRANSCRIPT_API_KEY=
DISCORD_WEBHOOK_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

## Getting started

```bash
# Run a single pipeline
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml

# Resume from a checkpoint after interruption
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml --resume outputs/<workspace_dir>

# Run all pipelines interactively
uv run python scripts/run_weekly_briefings.py
```

Available workflows live in `cognitive-assets/workflows/`: `news_research_pipeline` (global intelligence, HITL review), `sg_research_pipeline` (Singapore breadth scan), `tech_research_pipeline` (tech breadth scan).

Use `provider: "mock"` in any workflow step config to run without hitting an LLM API.

Two pipeline steps pause for human input (source review and missing content) — see [CLAUDE.md](CLAUDE.md#hitl-input-flow) for how that works.

## Learn more

See [CLAUDE.md](CLAUDE.md) for project structure, task development, checkpointing, LLM provider config, and workflow YAML conventions.
