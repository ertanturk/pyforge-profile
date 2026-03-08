"""State reset utilities for clearing profiling data.

This module provides functions to reset the Registry and prepare for
a new profiling cycle.
"""

from __future__ import annotations

from .registry import Registry


class Resetter:
    """Manages state reset between profiling runs."""

    @staticmethod
    def reset_all() -> None:
        """Reset all profiling data in Registry.

        Clears all registered function profiles, preparing the system
        for a fresh profiling cycle.
        """
        registry = Registry()
        registry.clear()
        print("[Resetter] Registry cleared. Ready for new profiling run.")

    @staticmethod
    def reset_metrics() -> None:
        """Reset only metrics while preserving registrations.

        Clears execution metrics (call_count, times, memory) for all
        registered functions while keeping their metadata.
        """
        registry = Registry()
        for profile in registry.all():
            profile.call_count = 0
            profile.total_time = 0.0
            profile.self_time = 0.0
            profile.memory_usage = 0.0
        print(f"[Resetter] Metrics reset for {len(list(registry.all()))} functions.")


# Convenience functions
def reset_all() -> None:
    """Reset all profiling data."""
    Resetter.reset_all()


def reset_metrics() -> None:
    """Reset only metrics while preserving function registrations."""
    Resetter.reset_metrics()
