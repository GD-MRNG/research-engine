# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Package management

Always use `uv`, never `pip`:

```bash
uv add <package>        # add a dependency
uv sync                 # install from uv.lock
uv run python <file>    # run with the venv active
```

Running scripts with bare `python` won't find project dependencies — always use `uv run python`.

## Running pipelines

```bash
# Single pipeline
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml

# Resume after interruption
uv run python main.py --workflow cognitive-assets/workflows/news_research_pipeline.yaml --resume outputs/<workspace_dir>

# All pipelines interactively
uv run python scripts/run_weekly_briefings.py
```

## Project structure

```
src/core/        — workflow engine: WorkflowEngine, WorkflowContext, task registry, LLM client
src/tasks/       — task implementations registered with @register_task
src/utils/       — scraping, YouTube, audio, documents, Discord, I/O helpers
scripts/         — standalone operator scripts (multi-pipeline runner, source quality audit)
cognitive-assets/ — separate git repo: workflows, prompts, source CSVs, Jinja2 templates
inputs/          — runtime input files (input.txt for HITL, not committed except as empty seed)
outputs/         — workspace dirs created per run (gitignored)
```

`cognitive-assets/` is a separate repo cloned into this directory. It is gitignored here. Changes to workflows or prompts must be committed there separately.

## Adding a task

1. Create or edit a file in `src/tasks/`
2. Decorate the class with `@register_task("TaskName")`
3. Implement `execute(self, context: WorkflowContext, config: Dict[str, Any]) -> WorkflowContext`
4. Import the module somewhere it gets loaded (e.g. `main.py`) — the decorator does the rest

## Checkpointing

Enrichment tasks write progress to a JSON checkpoint file after each item:

```python
artifact = CheckpointManager.load(checkpoint_file)
# ... modify items ...
CheckpointManager.save(checkpoint_file, artifact)
```

Checkpoint files live in the workspace dir (`outputs/<timestamp>/`). Pass `--resume outputs/<dir>` to skip already-completed items on re-run.

## HITL input flow

`SourceGatheringTask` and `ManualReviewTask` both pause for human input via `_prompt_file_input()` in `src/tasks/extractors.py`:

- Writes a `>>>` header to `inputs/input.txt` describing what's needed
- Waits for the user to paste content below the header, save, and press Enter
- `>>>` header lines are filtered out on read — user never needs to delete them
- Empty submit → one retry with a `RETRY —` header; second empty submit skips the item

## LLM providers

| Key | When to use |
|---|---|
| `ollama` | Local inference — region tagging, audit. No API key needed. |
| `poe` | Cloud inference — summarisation, synthesis, share summaries. Requires `POE_API_KEY`. |
| `mock` | Testing without API calls — returns empty strings for all LLM calls. |

## Workflow YAML

All file paths in workflow configs are relative to the engine's working directory (repo root), so `cognitive-assets/` paths are written as-is. The `checkpoint_file` path is relative to the run's workspace dir.

## Tests

```bash
uv run python tests/e2e/test_title_scraper.py --csv tests/e2e/inputs/title_urls.csv
uv run python tests/e2e/test_content_scraper.py --csv tests/e2e/inputs/content_urls.csv
```

Or run all steps including pipelines interactively via `scripts/run_weekly_briefings.py`.
