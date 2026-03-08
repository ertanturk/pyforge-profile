"""Programmatic API for pyforge-profile profiling framework.

This module provides the main user-facing API for profiling functions,
executing profiled code, and generating reports.
"""

from __future__ import annotations

from typing import Any

from .collector import profile  # Re-export decorator
from .executer import Executer
from .registry import Registry
from .reporter import Reporter
from .resetter import Resetter


def execute_function(
    func_name: str,
    file_name: str,
    line_number: int,
    *args: Any,
    timeout: float = 60.0,
    **kwargs: Any,
) -> None:
    """Execute a registered profiled function in isolated subprocess.

    Args:
        func_name: Name of the function to execute.
        file_name: Source file path where function is defined.
        line_number: Line number of function definition.
        *args: Positional arguments to pass to function.
        timeout: Maximum seconds to wait for execution. Defaults to 60.0.
        **kwargs: Keyword arguments to pass to function.

    Raises:
        ValueError: If function not found in registry.
        SerializationError: If arguments cannot be pickled.
        SubprocessTimeoutError: If execution exceeds timeout.
        SubprocessCrashError: If subprocess exits abnormally.
    """
    executer = Executer(timeout=timeout)
    executer.execute(func_name, file_name, line_number, *args, **kwargs)


def generate_report(*, show_children: bool = True) -> None:
    """Generate and print profiling report from all registered functions.

    Args:
        show_children: Whether to display child function calls.
    """
    reporter = Reporter(show_children=show_children)
    reporter.generate_report()


def reset_metrics() -> None:
    """Reset all profiling metrics while keeping function registrations.

    Use this between profiling runs to re-profile the same functions
    without losing their registration information.
    """
    Resetter.reset_metrics()


def reset_all() -> None:
    """Clear all profiling data including registrations.

    Use this for a complete reset between profiling sessions.
    """
    Resetter.reset_all()


def get_registry() -> Registry:
    """Get the global Registry singleton.

    Returns:
        The Registry instance containing all registered functions.
    """
    return Registry()


__all__ = [
    "execute_function",
    "generate_report",
    "get_registry",
    "profile",
    "reset_all",
    "reset_metrics",
]
