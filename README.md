# research-engine

A specialised workflow engine for web research pipelines that produce blog posts. Extracted from [cognitive-engine](../README.md) to enable independent development of the research and publishing stack.

## What it does

Runs three research pipelines end-to-end:

| Pipeline | Description |
|---|---|
| `news_research_pipeline` | Full global intelligence pipeline — scrapes sources, HITL review, regional categorisation, synthesis, publishes to Jekyll blog |
| `sg_research_pipeline` | Singapore-focused breadth scan — automated scraping, signal extraction, synthesis |
| `tech_research_pipeline` | Tech-focused breadth scan — automated scraping, signal extraction, synthesis |

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

## Running a pipeline

```bash
# Run a workflow
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml

# Resume from a checkpoint after interruption
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml --resume outputs/<workspace_dir>

# Debug logging
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml --debug

# Run all pipelines interactively
uv run python run_weekly_briefings.py
```

Use `provider: "mock"` in any workflow step config to run without hitting an LLM API.

## Project structure

```
research-engine/
├── main.py                     # Workflow runner entry point
├── run_weekly_briefings.py     # Interactive multi-pipeline orchestrator
├── src/
│   ├── core/                   # Workflow engine (engine, registry, context, LLM client)
│   ├── tasks/                  # Pipeline task implementations
│   │   ├── loaders.py          # SourceCSVLoader
│   │   ├── extractors.py       # SourceGatheringTask, ContentScrapingTask, TitleScrapingTask, ManualReviewTask
│   │   ├── transformers.py     # SummarizationTask, RegionCategorizationTask
│   │   ├── synthesis.py        # StrategicSynthesisTask, ReportGenerationTask, ShareSummaryTask
│   │   ├── delivery.py         # CloudArchivalTask, GitPublisherTask
│   │   ├── audit.py            # PipelineAuditTask
│   │   └── notifications.py    # NotificationTask
│   └── utils/                  # Web scraping, YouTube, audio, document, I/O, Discord
└── cognitive-assets/           # Cloned separately — workflows, prompts, templates, source CSVs
```

## LLM providers

| Provider + Model | Role |
|---|---|
| `poe` + `gemini-3.1-flash-lite` | Signal extraction (fast, cheap) |
| `poe` + `gemini-3.5-flash` | Synthesis (large context) |
| `poe` + `claude-haiku-4.5` | Share summary generation |
| `ollama` + `qwen2.5:14b` | Region categorisation (local) |
| `ollama` + `gemma4:latest` | Pipeline audit (local) |
| `mock` | Local testing without API calls |

## Checkpoint / resume

All enrichment tasks write to a JSON checkpoint file after each item. If a pipeline is interrupted, re-run with `--resume outputs/<workspace_dir>` to pick up where it left off.

## Relationship to cognitive-engine

This project is a focused extraction of the research/publishing stack from `cognitive-engine`. The core framework (`src/core/`) is duplicated rather than shared, so both repos can evolve independently. The classes migrated here are marked `# DEPRECATED: migrated to research-engine` in the original repo and will be removed from there once this project is validated.
