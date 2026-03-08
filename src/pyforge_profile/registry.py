from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import ValuesView

    from .entry import FunctionProfile


class Registry:
    """Singleton registry storing `FunctionProfile` instances keyed by location."""

    _instance = None

    def __new__(cls) -> Registry:
        """Return the singleton instance of `Registry`."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the internal mapping on first construction."""
        if not hasattr(self, "_registry"):
            self._registry: dict[str, FunctionProfile] = {}

    def _make_key(self, file_name: str, line_number: int, function_name: str) -> str:
        """Create a stable key for a function location."""
        return f"{file_name}:{line_number}:{function_name}"

    def register(self, function_profile: FunctionProfile) -> None:
        """Register or replace a `FunctionProfile` in the registry."""
        key = self._make_key(
            function_profile.file_name,
            function_profile.line_number,
            function_profile.name,
        )
        self._registry[key] = function_profile

    def get(self, file_name: str, line_number: int, function_name: str) -> FunctionProfile | None:
        """Return the profile for the given location, or `None` if missing."""
        key = self._make_key(file_name, line_number, function_name)
        return self._registry.get(key)

    def clear(self) -> None:
        """Remove all entries from the registry."""
        self._registry.clear()

    def all(self) -> ValuesView[FunctionProfile]:
        """Return a view of all stored `FunctionProfile` objects."""
        return self._registry.values()

    def __contains__(self, key: str) -> bool:
        """Return True if `key` exists in the registry."""
        return key in self._registry

    def __str__(self) -> str:
        """Human-readable representation listing registry keys."""
        return f"Registry with {len(self._registry)} entries: {list(self._registry.keys())}"

    def __len__(self) -> int:
        """Return number of entries in the registry."""
        return len(self._registry)

    def __repr__(self) -> str:
        """Machine-oriented representation of the registry."""
        return f"<Registry entries={len(self._registry)}>"
