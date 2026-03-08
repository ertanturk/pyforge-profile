from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class FunctionProfile:
    """Profiling data for a single function.

    Stores timing, memory, and call-count information plus child profiles.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        function_name: str,
        file_name: str,
        line_number: int,
        call_count: int = 0,
        total_time: float = 0.0,
        self_time: float = 0.0,
        memory_usage: float = 0.0,
    ):
        """Create a new `FunctionProfile` instance.

        Args:
            func: The callable being profiled.
            function_name: Function name.
            file_name: Source file path.
            line_number: Definition line number.
            call_count: Number of times the function has been called.
            total_time: Total execution time including children (seconds).
            self_time: Execution time excluding children (seconds).
            memory_usage: Memory used by this function (bytes or units).
        """
        self.function = func
        self.name = function_name
        self.file_name = file_name
        self.line_number = line_number
        self.call_count = call_count
        self.total_time = total_time
        self.self_time = self_time
        self.memory_usage = memory_usage
