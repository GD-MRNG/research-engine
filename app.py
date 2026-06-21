"""
Research Engine Launcher
Run: uv run python app.py
"""
import datetime
import logging
import os
import queue
import subprocess
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
    "SG Research": "cognitive-assets/workflows/sg_research_pipeline.yaml",
    "Tech Research": "cognitive-assets/workflows/tech_research_pipeline.yaml",
}

TESTS = [
    ["python", "tests/e2e/test_title_scraper.py", "--csv", "tests/e2e/inputs/title_urls.csv"],
    ["python", "tests/e2e/test_content_scraper.py", "--csv", "tests/e2e/inputs/content_urls.csv"],
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


def _run_pipeline(workflow_name: str):
    config_path = WORKFLOWS[workflow_name]
    now = datetime.datetime.now()
    workspace_dir = os.path.join("outputs", now.strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(workspace_dir, exist_ok=True)

    log_queue.put(f"▶  {workflow_name}")
    log_queue.put(f"   Workspace: {workspace_dir}")

    try:
        engine = WorkflowEngine(config_path, workspace_dir=workspace_dir)
        engine.context.set("_input_bridge", input_bridge)
        engine.run()
        log_queue.put(f"✓  {workflow_name} — done")
    except Exception as e:
        log_queue.put(f"✗  {workflow_name} — {e}")
    finally:
        _set_running(False)


def _run_tests():
    log_queue.put("▶  Running E2E tests...")
    for cmd in TESTS:
        log_queue.put(f"   $ {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in iter(proc.stdout.readline, ""):
                log_queue.put(f"   {line.rstrip()}")
            proc.wait()
            ok = proc.returncode == 0
            log_queue.put(f"   → {'PASSED ✓' if ok else f'FAILED ✗ (exit {proc.returncode})'}")
        except Exception as e:
            log_queue.put(f"   ERROR: {e}")
    log_queue.put("Tests complete.")
    _set_running(False)


def _launch(target_fn, *args):
    if _pipeline_running:
        log_queue.put("⚠  A pipeline is already running.")
        return
    _set_running(True)
    threading.Thread(target=target_fn, args=args, daemon=True).start()


# ── UI ─────────────────────────────────────────────────────────────────────────

def _drain_log(current: str) -> str:
    lines = []
    while True:
        try:
            lines.append(log_queue.get_nowait())
        except queue.Empty:
            break
    return current + "\n".join(lines) + ("\n" if lines else "")


def build_ui():
    with gr.Blocks(title="Research Engine", theme=gr.themes.Soft()) as app:
        gr.Markdown("# Research Engine")

        # Controls
        with gr.Row():
            btn_tests = gr.Button("Run Tests", variant="secondary", scale=1)
            gr.Column(scale=3)  # spacer
        with gr.Row():
            btn_news = gr.Button("▶  News Research (HITL)", variant="primary")
            btn_sg   = gr.Button("▶  SG Research",          variant="primary")
            btn_tech = gr.Button("▶  Tech Research",         variant="primary")

        # Log
        gr.Markdown("### Log")
        log_box = gr.Textbox(
            value="Ready.\n",
            lines=20,
            max_lines=20,
            interactive=False,
            show_label=False,
            autoscroll=True,
        )
        log_state = gr.State("Ready.\n")

        # HITL input panel — hidden until bridge signals
        with gr.Group(visible=False) as input_panel:
            gr.Markdown("### ⚠ Input Required")
            prompt_md  = gr.Markdown("")
            context_md = gr.Markdown("")
            input_box  = gr.Textbox(
                label="Your input",
                lines=8,
                placeholder="Paste URLs or content here, then click Submit.",
            )
            submit_btn = gr.Button("Submit", variant="primary")

        # Timer — polls log queue and input bridge every 500 ms
        timer = gr.Timer(value=0.5)
        all_btns = [btn_tests, btn_news, btn_sg, btn_tech]

        @timer.tick(
            inputs=[log_state],
            outputs=[log_state, log_box, input_panel, prompt_md, context_md, *all_btns],
        )
        def poll(current_log):
            updated = _drain_log(current_log)
            pending = input_bridge.get_pending()
            busy    = _pipeline_running
            btn_upd = gr.update(interactive=not busy)

            panel_visible = gr.update(visible=bool(pending))
            prompt_upd    = gr.update(value=f"**{pending['prompt']}**" if pending else "")
            context_upd   = gr.update(value=pending["context"] if pending else "")

            return (updated, gr.update(value=updated), panel_visible,
                    prompt_upd, context_upd, *[btn_upd] * 4)

        @submit_btn.click(inputs=[input_box], outputs=[input_box, input_panel])
        def on_submit(text):
            input_bridge.respond(text.strip())
            return gr.update(value=""), gr.update(visible=False)

        btn_tests.click(fn=lambda: _launch(_run_tests))
        btn_news.click( fn=lambda: _launch(_run_pipeline, "News Research (HITL)"))
        btn_sg.click(   fn=lambda: _launch(_run_pipeline, "SG Research"))
        btn_tech.click( fn=lambda: _launch(_run_pipeline, "Tech Research"))

    return app


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860)
