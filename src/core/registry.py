from typing import Type, Dict
from src.core.interfaces import PipelineTask

# Internal storage for mapping task_type names to classes
_TASK_REGISTRY: Dict[str, Type[PipelineTask]] = {}


class TaskNotFoundError(Exception):
    """Raised when a requested task type is not found in the registry."""

    pass


def register_task(name: str):
    """
    A class decorator to register a PipelineTask.

    Usage:
        @register_task("MyTask")
        class MyTask(PipelineTask):
            ...
    """

    def decorator(cls: Type[PipelineTask]):
        if name in _TASK_REGISTRY:
            raise ValueError(f"Task '{name}' is already registered.")
        _TASK_REGISTRY[name] = cls
        return cls

    return decorator


def get_task_class(name: str) -> Type[PipelineTask]:
    """
    Retrieves the class type for a given task name.
    """
    if name not in _TASK_REGISTRY:
        raise TaskNotFoundError(
            f"Task '{name}' not found. Did you forget to import it?"
        )
    return _TASK_REGISTRY[name]


def list_registered_tasks() -> list[str]:
    """Returns a list of all available tasks."""
    return list(_TASK_REGISTRY.keys())
