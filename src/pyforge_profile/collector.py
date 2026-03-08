"""Function collection and profiling data extraction.

This module provides the `profile` decorator that introspects functions,
extracts metadata using `inspect` and `ast`, and registers profiling data
in the Registry singleton.
"""

from __future__ import annotations

import ast
import functools
import inspect
from collections.abc import Callable
from typing import Any

from .entry import FunctionProfile
from .registry import Registry


class ChildFunctionCall:
    """Metadata for a child function call discovered via AST analysis.

    Attributes:
        name: The name of the called function.
        args_count: Number of positional arguments passed.
        kwargs_names: Names of keyword arguments passed.
        is_async: Whether the call is awaited (async call).
    """

    def __init__(
        self,
        name: str,
        args_count: int,
        kwargs_names: list[str],
        *,
        is_async: bool,
    ) -> None:
        """Initialize child function call metadata.

        Args:
            name: Name of the called function.
            args_count: Count of positional arguments.
            kwargs_names: List of keyword argument names.
            is_async: Whether this is an async call.
        """
        self.name = name
        self.args_count = args_count
        self.kwargs_names = kwargs_names
        self.is_async = is_async

    def __repr__(self) -> str:
        """Return machine-readable representation."""
        return (
            f"ChildFunctionCall(name={self.name!r}, args={self.args_count}, "
            f"kwargs={self.kwargs_names}, async={self.is_async})"
        )


class FunctionAnalyzer:
    """AST-based analyzer for extracting child function calls and metadata."""

    def __init__(self, func: Callable[..., Any]) -> None:
        """Initialize analyzer with a function.

        Args:
            func: The function to analyze.

        Raises:
            TypeError: If source code cannot be retrieved.
        """
        self.func = func
        self.source = inspect.getsource(func)
        try:
            self.tree = ast.parse(self.source)
        except SyntaxError as exc:
            msg = f"Failed to parse source for {func.__name__}: {exc}"
            raise TypeError(msg) from exc

    def extract_child_calls(self) -> list[ChildFunctionCall]:
        """Extract all child function calls from the function's AST.

        Returns:
            List of ChildFunctionCall objects representing all calls found.
        """
        child_calls: list[ChildFunctionCall] = []
        await_nodes: set[int] = set()

        # First pass: identify which calls are awaited
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
                await_nodes.add(id(node.value))

        # Second pass: extract call information
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                # Extract function name
                func_name = self._extract_call_name(node)
                if func_name is None:
                    continue

                # Count arguments
                args_count = len(node.args)
                kwargs_names = [kw.arg for kw in node.keywords if kw.arg]

                # Check if this call is awaited
                is_async = id(node) in await_nodes

                child_calls.append(
                    ChildFunctionCall(
                        name=func_name,
                        args_count=args_count,
                        kwargs_names=kwargs_names,
                        is_async=is_async,
                    )
                )

        return child_calls

    def _extract_call_name(self, node: ast.Call) -> str | None:
        """Extract the function name from a Call node.

        Args:
            node: The ast.Call node.

        Returns:
            The function name, or None if it cannot be determined.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            # For calls like obj.method(), return "method"
            return node.func.attr
        return None

    def has_inner_async_functions(self) -> bool:
        """Check if the function defines any inner async functions.

        Returns:
            True if any AsyncFunctionDef is found in the function body.
        """
        for node in ast.walk(self.tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name != self.func.__name__:
                # Exclude the main function itself
                return True
        return False


def profile[FuncType: Callable[..., Any]](func: FuncType) -> FuncType:
    """Decorator to profile a function and track its execution.

    This decorator:
    1. Validates that the target is callable
    2. Detects if the function is asynchronous
    3. Extracts source code location (file and line number)
    4. Performs AST analysis to discover child function calls
    5. Creates a FunctionProfile entry and registers it

    Args:
        func: The function to profile.

    Returns:
        The original function (wrapped to preserve signature).

    Raises:
        TypeError: If the target is not callable or source cannot be parsed.
    """
    # Check 1: Ensure the target is callable
    if not callable(func):
        msg = f"profile decorator requires a callable, got {type(func).__name__}"
        raise TypeError(msg)

    # Extract basic function metadata
    file_name = inspect.getsourcefile(func) or "<unknown>"
    source_lines = inspect.getsourcelines(func)
    line_number = source_lines[1]

    # Check 2: Detect if function is async
    is_async = inspect.iscoroutinefunction(func)

    # Check 3: Analyze function via AST for child calls
    try:
        analyzer = FunctionAnalyzer(func)
        child_calls = analyzer.extract_child_calls()
        has_inner_async = analyzer.has_inner_async_functions()
    except TypeError as exc:
        # If AST analysis fails, log but don't fail the decorator
        child_calls = []
        has_inner_async = False
        print(f"[Collector] Warning: AST analysis failed for {func.__name__}: {exc}")

    # Create FunctionProfile entry
    profile_entry = FunctionProfile(
        func=func,
        function_name=func.__name__,
        file_name=file_name,
        line_number=line_number,
        call_count=0,
        total_time=0.0,
        self_time=0.0,
        memory_usage=0.0,
    )

    # Attach metadata to profile for reference
    profile_entry.metadata = {  # type: ignore[attr-defined]
        "is_async": is_async,
        "child_calls": child_calls,
        "has_inner_async": has_inner_async,
    }

    # Register in singleton Registry
    registry = Registry()
    registry.register(profile_entry)

    print(
        f"[Collector] Registered {func.__name__} at {file_name}:{line_number} "
        f"(async={is_async}, children={len(child_calls)})"
    )

    # Return wrapped function that preserves original signature
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper that executes the profiled function.

        Validates arguments against function signature before execution.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The return value from the original function.

        Raises:
            TypeError: If arguments don't match the function signature.
        """
        # Check 4: Validate parameters using inspect.signature().bind()
        try:
            signature = inspect.signature(func)
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
        except TypeError as exc:
            msg = f"Invalid arguments for {func.__name__}: {exc}"
            raise TypeError(msg) from exc

        # Execute the original function
        return func(*args, **kwargs)

    # For async functions, create an async wrapper
    if is_async:

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper that executes the profiled async function.

            Validates arguments against function signature before execution.

            Args:
                *args: Positional arguments to pass to the function.
                **kwargs: Keyword arguments to pass to the function.

            Returns:
                The return value from the original async function.

            Raises:
                TypeError: If arguments don't match the function signature.
            """
            # Validate parameters for async functions too
            try:
                signature = inspect.signature(func)
                bound_args = signature.bind(*args, **kwargs)
                bound_args.apply_defaults()
            except TypeError as exc:
                msg = f"Invalid arguments for {func.__name__}: {exc}"
                raise TypeError(msg) from exc

            # Execute the original async function
            return await func(*args, **kwargs)

        return async_wrapper  # type: ignore[return-value]

    return wrapper  # type: ignore[return-value]
