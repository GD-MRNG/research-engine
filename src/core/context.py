import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WorkflowContext:
    """
    A robust state container that acts as the shared memory for a workflow run.
    Handles data passing between tasks and supports serialization for checkpointing.
    """

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        # We use a protected dict to encourage use of get/set methods
        self._state: Dict[str, Any] = initial_state if initial_state else {}

    def set(self, key: str, value: Any) -> None:
        """
        Updates the context state.
        Args:
            key: The identifier for the data.
            value: The data to store (must be serializable if checkpointing is used).
        """
        self._state[key] = value
        logger.debug(f"Context updated: '{key}' set.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves data from the context.
        """
        return self._state.get(key, default)

    def require(self, key: str) -> Any:
        """
        Retrieves data or raises an error if missing.
        Use this when a Task strictly depends on a specific input.
        """
        if key not in self._state:
            error_msg = f"Missing required context key: '{key}'"
            logger.error(error_msg)
            raise KeyError(error_msg)
        return self._state[key]

    def save_to_disk(self, filepath: str) -> None:
        """
        Serializes the current state to a JSON file.
        Useful for debugging or resuming workflows.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, default=str)
            logger.info(f"Context saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save context to {filepath}: {e}")
            raise

    def load_from_disk(self, filepath: str) -> None:
        """
        Loads state from a JSON file, merging/overwriting current state.
        """
        if not os.path.exists(filepath):
            logger.warning(f"Context file not found: {filepath}")
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                self._state.update(data)
            logger.info(f"Context loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load context from {filepath}: {e}")
            raise
