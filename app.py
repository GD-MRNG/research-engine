"""
Research Engine Launcher
Run: uv run python app.py
"""
import datetime
import logging
import os
import queue
import subprocess
import sys
import threading

import gradio as gr
from dotenv import load_dotenv

from src.core.engine import WorkflowEngine
from src.ui.input_bridge import InputBridge

load_dotenv()

# ── Global state ───────────────────────────────────────────────────────────────

log_queue: queue.Queue[str] = queue.Queue()
input_bridge = InputBridge()
_pipeline_running = False

WORKFLOWS = {
    "News Research (HITL)": "cognitive-assets/workflows/news_research_pipeline.yaml",
    "SG Research":          "cognitive-assets/workflows/sg_research_pipeline.yaml",
    "Tech Research":        "cognitive-assets/workflows/tech_research_pipeline.yaml",
}

WEEKLY_STEPS = [
    {"label": "E2E: Title Scraper",               "group": "tests",    "cmd": [sys.executable, "tests/e2e/test_title_scraper.py",   "--csv", "tests/e2e/inputs/title_urls.csv"]},
    {"label": "E2E: Content Scraper",             "group": "tests",    "cmd": [sys.executable, "tests/e2e/test_content_scraper.py", "--csv", "tests/e2e/inputs/content_urls.csv"]},
    {"label": "Pipeline: SG Research",            "group": "pipeline", "workflow": "SG Research"},
    {"label": "Pipeline: Tech Research",          "group": "pipeline", "workflow": "Tech Research"},
    {"label": "Pipeline: News Research (HITL)",   "group": "pipeline", "workflow": "News Research (HITL)"},
]

# Status for each weekly step: "pending" | "running" | "passed" | "failed" | "skipped"
_step_statuses: list[str] = ["pending"] * len(WEEKLY_STEPS)

TESTS = [
    [sys.executable, "tests/e2e/test_title_scraper.py",   "--csv", "tests/e2e/inputs/title_urls.csv"],
    [sys.executable, "tests/e2e/test_content_scraper.py", "--csv", "tests/e2e/inputs/content_urls.csv"],
]

# ── Logging ────────────────────────────────────────────────────────────────────

class _QueueLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        log_queue.put(self.format(record))

_handler = _QueueLogHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(_handler)
logging.getLogger().setLevel(logging.INFO)

# ── Runners ────────────────────────────────────────────────────────────────────

def _set_running(state: bool):
    global _pipeline_running
    _pipeline_running = state


def _run_subprocess(cmd: list[str], label: str) -> bool:
    log_queue.put(f"   $ {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(proc.stdout.readline, ""):
            log_queue.put(f"   {line.rstrip()}")
        proc.wait()
        ok = proc.returncode == 0
        log_queue.put(f"   → {'PASSED ✓' if ok else f'FAILED ✗ (exit {proc.returncode})'}")
        return ok
    except Exception as e:
        log_queue.put(f"   ERROR: {e}")
        return False


def _run_pipeline_step(workflow_name: str) -> bool:
    config_path = WORKFLOWS[workflow_name]
    now = datetime.datetime.now()
    workspace_dir = os.path.join("outputs", now.strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(workspace_dir, exist_ok=True)
    log_queue.put(f"   Workspace: {workspace_dir}")
    try:
        engine = WorkflowEngine(config_path, workspace_dir=workspace_dir)
        engine.context.set("_input_bridge", input_bridge)
        engine.run()
        return True
    except Exception as e:
        log_queue.put(f"   ERROR: {e}")
        return False


def _run_weekly():
    global _step_statuses
    _step_statuses = ["pending"] * len(WEEKLY_STEPS)
    log_queue.put("━━━ Weekly Run ━━━")

    for i, step in enumerate(WEEKLY_STEPS):
        _step_statuses[i] = "running"
        log_queue.put(f"\n── Step {i+1}/{len(WEEKLY_STEPS)}: {step['label']}")

        if step["group"] == "tests":
            ok = _run_subprocess(step["cmd"], step["label"])
        else:
            ok = _run_pipeline_step(step["workflow"])

        _step_statuses[i] = "passed" if ok else "failed"

        if not ok and step["group"] == "tests":
            log_queue.put("⚠  Tests failed — continuing to pipelines.")

    passed = sum(1 for s in _step_statuses if s == "passed")
    failed = sum(1 for s in _step_statuses if s == "failed")
    log_queue.put(f"\n━━━ Done: {passed} passed, {failed} failed ━━━")
    _set_running(False)


def _run_pipeline(workflow_name: str):
    log_queue.put(f"▶  {workflow_name}")
    ok = _run_pipeline_step(workflow_name)
    log_queue.put(f"{'✓' if ok else '✗'}  {workflow_name} — {'done' if ok else 'failed'}")
    _set_running(False)


def _run_tests():
    log_queue.put("▶  Running E2E tests...")
    for cmd in TESTS:
        _run_subprocess(cmd, "")
    log_queue.put("Tests complete.")
    _set_running(False)


def _launch(target_fn, *args):
    if _pipeline_running:
        log_queue.put("⚠  A pipeline is already running.")
        return
    _set_running(True)
    threading.Thread(target=target_fn, args=args, daemon=True).start()


# ── UI helpers ─────────────────────────────────────────────────────────────────

_ICONS = {"pending": "⬜", "running": "▶️", "passed": "✅", "failed": "❌", "skipped": "⏭️"}


def _render_steps() -> str:
    rows = []
    for i, (step, status) in enumerate(zip(WEEKLY_STEPS, _step_statuses)):
        icon = _ICONS.get(status, "⬜")
        rows.append(f"{icon} &nbsp; **Step {i+1}:** {step['label']}")
    return "\n\n".join(rows)


def _drain_log(current: str) -> str:
    lines = []
    while True:
        try:
            lines.append(log_queue.get_nowait())
        except queue.Empty:
            break
    return current + "\n".join(lines) + ("\n" if lines else "")


# ── HITL panel (shared across tabs) ───────────────────────────────────────────

def _hitl_panel():
    with gr.Group(visible=False) as panel:
        gr.Markdown("### ⚠ Input Required")
        prompt_md  = gr.Markdown("")
        context_md = gr.Markdown("")
        input_box  = gr.Textbox(
            label="Your input",
            lines=8,
            placeholder="Paste URLs or content here, then click Submit.",
        )
        submit_btn = gr.Button("Submit", variant="primary")
    return panel, prompt_md, context_md, input_box, submit_btn


# ── Build UI ───────────────────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(title="Research Engine", theme=gr.themes.Soft()) as app:
        gr.Markdown("# Research Engine")

        log_state = gr.State("Ready.\n")

        with gr.Tabs():

            # ── Tab 1: Weekly Run ──────────────────────────────────────────────
            with gr.Tab("Weekly Run"):
                btn_weekly = gr.Button("▶  Run Weekly", variant="primary", size="lg")

                gr.Markdown("### Steps")
                steps_md = gr.Markdown(_render_steps())

                gr.Markdown("### Log")
                log_box_w = gr.Textbox(
                    value="Ready.\n",
                    lines=20,
                    max_lines=20,
                    interactive=False,
                    show_label=False,
                    autoscroll=True,
                )

                panel_w, prompt_w, context_w, input_box_w, submit_w = _hitl_panel()

            # ── Tab 2: Pipelines ───────────────────────────────────────────────
            with gr.Tab("Pipelines"):
                with gr.Row():
                    btn_tests = gr.Button("Run Tests", variant="secondary", scale=1)
                    gr.Column(scale=3)
                with gr.Row():
                    btn_news = gr.Button("▶  News Research (HITL)", variant="primary")
                    btn_sg   = gr.Button("▶  SG Research",          variant="primary")
                    btn_tech = gr.Button("▶  Tech Research",         variant="primary")

                gr.Markdown("### Log")
                log_box_p = gr.Textbox(
                    value="Ready.\n",
                    lines=20,
                    max_lines=20,
                    interactive=False,
                    show_label=False,
                    autoscroll=True,
                )

                panel_p, prompt_p, context_p, input_box_p, submit_p = _hitl_panel()

        # ── Timer (500 ms) ─────────────────────────────────────────────────────
        timer = gr.Timer(value=0.5)
        all_btns = [btn_weekly, btn_tests, btn_news, btn_sg, btn_tech]

        @timer.tick(
            inputs=[log_state],
            outputs=[
                log_state, log_box_w, log_box_p, steps_md,
                panel_w, prompt_w, context_w,
                panel_p, prompt_p, context_p,
                *all_btns,
            ],
        )
        def poll(current_log):
            updated  = _drain_log(current_log)
            log_upd  = gr.update(value=updated)
            pending  = input_bridge.get_pending()
            busy     = _pipeline_running
            btn_upd  = gr.update(interactive=not busy)

            panel_upd   = gr.update(visible=bool(pending))
            prompt_upd  = gr.update(value=f"**{pending['prompt']}**" if pending else "")
            context_upd = gr.update(value=pending["context"] if pending else "")

            return (
                updated, log_upd, log_upd, gr.update(value=_render_steps()),
                panel_upd, prompt_upd, context_upd,
                panel_upd, prompt_upd, context_upd,
                *[btn_upd] * 5,
            )

        # ── Button wiring ──────────────────────────────────────────────────────
        btn_weekly.click(fn=lambda: _launch(_run_weekly))
        btn_tests.click( fn=lambda: _launch(_run_tests))
        btn_news.click(  fn=lambda: _launch(_run_pipeline, "News Research (HITL)"))
        btn_sg.click(    fn=lambda: _launch(_run_pipeline, "SG Research"))
        btn_tech.click(  fn=lambda: _launch(_run_pipeline, "Tech Research"))

        for input_box, submit_btn, panel in [
            (input_box_w, submit_w, panel_w),
            (input_box_p, submit_p, panel_p),
        ]:
            submit_btn.click(
                fn=lambda text, p=panel: (input_bridge.respond(text.strip()), gr.update(value=""), gr.update(visible=False))[1:],
                inputs=[input_box],
                outputs=[input_box, panel],
            )

    return app


if __name__ == "__main__":
    build_ui().launch(server_name="127.0.0.1", server_port=7860)
