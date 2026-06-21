import queue


class InputBridge:
    """
    Thread-safe bridge for HITL input between pipeline tasks (background thread)
    and the Gradio UI (main thread).

    Pipeline tasks call request() which blocks until the UI calls respond().
    The UI polls get_pending() to detect waiting tasks without consuming the request.
    """

    def __init__(self):
        self._response_queue: queue.Queue[str] = queue.Queue()
        self._pending: dict | None = None

    def request(self, prompt: str, context: str = "") -> str:
        """Called by a pipeline task on a background thread. Blocks until UI responds."""
        self._pending = {"prompt": prompt, "context": context}
        return self._response_queue.get()

    def respond(self, text: str) -> None:
        """Called by the UI submit handler. Unblocks the waiting task."""
        self._pending = None
        self._response_queue.put(text)

    def get_pending(self) -> dict | None:
        """Non-destructive peek — returns the current pending request or None."""
        return self._pending
