"""Function execution and profiling in isolated subprocesses.

This module handles the execution phase of profiling by spawning isolated
subprocesses to measure execution time, memory usage, and CPU time without
interference from the main process.
"""

from __future__ import annotations

import asyncio
import gc
import inspect
import multiprocessing
import pickle  # nosec: B403 - pickle used for safe serializability checks only
import sys
import time
import tracemalloc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ProfileMetrics:
    """Metrics collected during function execution.

    Attributes:
        wall_time: Elapsed wall-clock time in seconds.
        cpu_time: CPU time used in seconds.
        peak_memory: Peak memory usage in bytes.
        call_count: Number of times the function was called.
    """

    wall_time: float
    cpu_time: float
    peak_memory: float
    call_count: int


class SerializationError(Exception):
    """Raised when function arguments cannot be serialized."""


class SubprocessTimeoutError(Exception):
    """Raised when subprocess execution exceeds timeout."""


class SubprocessCrashError(Exception):
    """Raised when subprocess exits with non-zero code."""


# Signal code for SIGKILL (OOM kill)
_SIGKILL_EXIT_CODE = -9


def _profile_worker(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    queue: multiprocessing.Queue[ProfileMetrics],
) -> None:
    """Worker function that runs in isolated subprocess.

    Disables garbage collection, performs warm-up + profiling iterations,
    and sends metrics back via queue.

    Args:
        func: The function to profile.
        args: Positional arguments for the function.
        kwargs: Keyword arguments for the function.
        queue: Queue for sending metrics back to main process.
    """
    try:
        # Disable garbage collection for clean measurements
        gc.disable()

        # Warm-up iteration: execute once without tracking
        try:
            if inspect.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
        except Exception as warmup_err:
            queue.put(None)  # type: ignore[arg-type]
            print(
                f"[Executer] Warm-up failed for {func.__name__}: {warmup_err}",
                file=sys.stderr,
            )
            return

        # Start memory tracking
        tracemalloc.start()

        # Record start times
        wall_start = time.perf_counter()
        cpu_start = time.process_time()

        # Profiling iteration: execute again with tracking
        call_count = 1
        try:
            if inspect.iscoroutinefunction(func):
                asyncio.run(func(*args, **kwargs))
            else:
                func(*args, **kwargs)
        except Exception as exec_err:
            queue.put(None)  # type: ignore[arg-type]
            print(
                f"[Executer] Profiling iteration failed: {exec_err}",
                file=sys.stderr,
            )
            return

        # Record end times
        wall_end = time.perf_counter()
        cpu_end = time.process_time()

        # Extract peak memory usage
        _current, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate metrics
        metrics = ProfileMetrics(
            wall_time=wall_end - wall_start,
            cpu_time=cpu_end - cpu_start,
            peak_memory=peak_memory,
            call_count=call_count,
        )

        queue.put(metrics)
    except Exception as err:
        print(f"[Executer] Worker error: {err}", file=sys.stderr)
        queue.put(None)  # type: ignore[arg-type]
    finally:
        # Re-enable garbage collection
        gc.enable()


class Executer:
    """Manages function execution in isolated subprocesses.

    Handles serialization validation, subprocess spawning, timeout management,
    and metrics collection from profiled function execution.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        """Initialize Executer with timeout setting.

        Args:
            timeout: Maximum seconds to wait for subprocess completion.
        """
        self.timeout = timeout

    def _validate_serializability(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """Validate that function and arguments can be pickled.

        Args:
            func: The function to check.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Raises:
            SerializationError: If any component cannot be serialized.
        """
        # Serializability Check: Verify picklability
        try:
            pickle.dumps(func)
        except (pickle.PicklingError, TypeError) as err:
            raise SerializationError(
                f"Function {func.__name__} cannot be serialized: {err}"
            ) from err

        for i, arg in enumerate(args):
            try:
                pickle.dumps(arg)
            except (pickle.PicklingError, TypeError) as err:
                raise SerializationError(
                    f"Positional argument {i} cannot be serialized: {err}"
                ) from err

        for key, value in kwargs.items():
            try:
                pickle.dumps(value)
            except (pickle.PicklingError, TypeError) as err:
                raise SerializationError(
                    f"Keyword argument '{key}' cannot be serialized: {err}"
                ) from err

    def execute(
        self,
        func_name: str,
        file_name: str,
        line_number: int,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute a registered function and collect profiling metrics.

        Retrieves function metadata from Registry, validates arguments,
        spawns subprocess, collects metrics, and updates Registry.

        Args:
            func_name: Name of the function to execute.
            file_name: Source file path of the function.
            line_number: Line number where function is defined.
            *args: Positional arguments to pass to function.
            **kwargs: Keyword arguments to pass to function.

        Raises:
            ValueError: If function not found in Registry.
            SerializationError: If arguments cannot be serialized.
            SubprocessTimeoutError: If subprocess exceeds timeout.
            SubprocessCrashError: If subprocess exits with error.
        """
        # Retrieval: Fetch from Registry
        registry = Registry()
        profile_entry = registry.get(file_name, line_number, func_name)

        if profile_entry is None:
            raise ValueError(f"Function {func_name} not found at {file_name}:{line_number}")

        func = profile_entry.function

        # Serialization: Validate all components are picklable
        self._validate_serializability(func, args, dict(kwargs))

        # Async Routing Check: Read metadata
        metadata = getattr(profile_entry, "metadata", {})
        is_async = metadata.get("is_async", False)

        print(f"[Executer] Executing {func.__name__} (async={is_async})")

        # Process Spawning: Create isolated subprocess with spawn context
        # Uses spawn instead of fork to ensure tracemalloc accuracy and avoid
        # deadlocks from inherited thread state
        ctx = multiprocessing.get_context("spawn")
        queue: multiprocessing.Queue[ProfileMetrics | None] = ctx.Queue()
        process = ctx.Process(
            target=_profile_worker,
            args=(func, args, dict(kwargs), queue),
            daemon=False,
        )
        process.start()

        # Timeout Check: Wait with timeout
        process.join(timeout=self.timeout)

        if process.is_alive():
            # Subprocess exceeded timeout - terminate
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
            raise SubprocessTimeoutError(f"Function {func_name} exceeded timeout ({self.timeout}s)")

        # Process Health Check: Verify exit code
        if process.exitcode is not None and process.exitcode != 0:
            # Check for OOM (signal 9) or other abnormal exit
            if process.exitcode == _SIGKILL_EXIT_CODE:
                raise SubprocessCrashError(
                    f"Function {func_name} killed (likely OOM). Exit code: {process.exitcode}"
                )
            raise SubprocessCrashError(f"Subprocess exited with code {process.exitcode}")

        # Data Registration: Read metrics from queue
        try:
            metrics = queue.get(timeout=2)
        except Exception as err:
            raise SubprocessCrashError(f"Failed to retrieve metrics: {err}") from err

        if not isinstance(metrics, ProfileMetrics):
            raise SubprocessCrashError("Worker returned None metrics")

        # Update Registry with collected metrics
        profile_entry.call_count += metrics.call_count
        profile_entry.total_time += metrics.wall_time
        profile_entry.self_time += metrics.cpu_time
        profile_entry.memory_usage = max(profile_entry.memory_usage, metrics.peak_memory)


# Convenience function for single execution
def execute_profiled(
    func_name: str,
    file_name: str,
    line_number: int,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Execute a registered profiled function.

    Args:
        func_name: Name of the function.
        file_name: Source file path.
        line_number: Definition line number.
        *args: Function arguments.
        **kwargs: Function keyword arguments.
    """
    executer = Executer()
    try:
        executer.execute(func_name, file_name, line_number, *args, **kwargs)
    except Exception as err:
        print(f"[Executer] Execution failed: {err}")
