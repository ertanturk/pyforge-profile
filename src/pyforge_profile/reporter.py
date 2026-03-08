"""Profiling data reporting with formatted terminal output.

This module formats and displays profiling results collected from the Registry
with bold terminal colors and organized output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .registry import Registry

if TYPE_CHECKING:
    from .entry import FunctionProfile


_TIME_MICROSECOND_THRESHOLD = 0.001
_TIME_MILLISECOND_THRESHOLD = 1
_MEMORY_KB_BOUNDARY = 1024
_MEMORY_MB_BOUNDARY = 1024
_MEMORY_GB_BOUNDARY = 1024
_CHILDREN_DISPLAY_LIMIT = 5


class _Color:
    """ANSI bold color codes."""

    RESET = "\033[0m"
    WHITE = "\033[1;37m"
    CYAN = "\033[1;36m"
    YELLOW = "\033[1;33m"
    GREEN = "\033[1;32m"
    MAGENTA = "\033[1;35m"
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"


def _format_time(seconds: float) -> str:
    """Format seconds into readable time string."""
    if seconds < _TIME_MICROSECOND_THRESHOLD:
        return f"{seconds * 1_000_000:.2f}μs"
    if seconds < _TIME_MILLISECOND_THRESHOLD:
        return f"{seconds * 1000:.2f}ms"
    return f"{seconds:.2f}s"


def _format_memory(bytes_val: float) -> str:
    """Format bytes into readable memory string."""
    if bytes_val < _MEMORY_KB_BOUNDARY:
        return f"{bytes_val:.0f}B"
    kb = bytes_val / _MEMORY_KB_BOUNDARY
    if kb < _MEMORY_MB_BOUNDARY:
        return f"{kb:.2f}KB"
    mb = kb / _MEMORY_MB_BOUNDARY
    if mb < _MEMORY_GB_BOUNDARY:
        return f"{mb:.2f}MB"
    gb = mb / _MEMORY_GB_BOUNDARY
    return f"{gb:.2f}GB"


class Reporter:
    """Generates formatted profiling reports from Registry data."""

    def __init__(self, *, show_children: bool = True) -> None:
        """Initialize Reporter.

        Args:
            show_children: Whether to display child function calls.
        """
        self.show_children = show_children

    def _format_metrics(self, profile: FunctionProfile) -> str:
        """Format profile metrics into a single line."""
        metrics: list[str] = []
        if profile.call_count > 0:
            metrics.append(f"calls={_Color.GREEN}{profile.call_count}{_Color.RESET}")
        if profile.total_time > 0:
            metrics.append(f"total={_Color.BLUE}{_format_time(profile.total_time)}{_Color.RESET}")
        if profile.self_time > 0:
            metrics.append(f"cpu={_Color.MAGENTA}{_format_time(profile.self_time)}{_Color.RESET}")
        if profile.memory_usage > 0:
            metrics.append(f"mem={_Color.RED}{_format_memory(profile.memory_usage)}{_Color.RESET}")
        return " | ".join(metrics) if metrics else ""

    def _print_child_calls(self, profile: FunctionProfile, indent: str) -> None:
        """Print child function calls metadata."""
        metadata = getattr(profile, "metadata", {})
        child_calls = metadata.get("child_calls", [])
        if not child_calls:
            return

        count_str = f"{_Color.YELLOW}{len(child_calls)}{_Color.RESET}"
        print(f"{indent}  → {count_str} child calls:")

        for child_call in child_calls[:_CHILDREN_DISPLAY_LIMIT]:
            args_str = f"{_Color.GREEN}{child_call.args_count}{_Color.RESET}"
            async_tag = f" {_Color.MAGENTA}async{_Color.RESET}" if child_call.is_async else ""
            kwargs_str = (
                f", {_Color.GREEN}{', '.join(child_call.kwargs_names)}{_Color.RESET}"
                if child_call.kwargs_names
                else ""
            )
            signature = f"{child_call.name}({args_str} args{kwargs_str}){async_tag}"
            print(f"{indent}    • {signature}")

        if len(child_calls) > _CHILDREN_DISPLAY_LIMIT:
            remaining = len(child_calls) - _CHILDREN_DISPLAY_LIMIT
            print(f"{indent}    • ... {_Color.YELLOW}{remaining}{_Color.RESET} more")

    def _print_profile(self, profile: FunctionProfile) -> None:
        """Print a single profile entry."""
        name_str = f"{_Color.WHITE}{profile.name}{_Color.RESET}"
        loc_str = f"{_Color.YELLOW}({profile.file_name}:{profile.line_number}){_Color.RESET}"
        print(f"  {name_str} {loc_str}")

        metrics = self._format_metrics(profile)
        if metrics:
            print(f"    {metrics}")

        if self.show_children:
            self._print_child_calls(profile, "  ")
        print()

    def generate_report(self) -> None:
        """Generate and print profiling report from Registry."""
        registry = Registry()
        profiles = list(registry.all())

        if not profiles:
            print(f"\n{_Color.YELLOW}No profiled functions in registry.{_Color.RESET}\n")
            return

        print(f"\n{_Color.CYAN}{'─' * 80}{_Color.RESET}")
        print(f"{_Color.CYAN}Profiling Report  {_Color.WHITE}pyforge-profile{_Color.RESET}")
        print(f"{_Color.CYAN}{'─' * 80}{_Color.RESET}\n")

        # Group by file
        by_file: dict[str, list[FunctionProfile]] = {}
        for profile in profiles:
            if profile.file_name not in by_file:
                by_file[profile.file_name] = []
            by_file[profile.file_name].append(profile)

        total_time = 0.0
        total_memory = 0.0
        total_calls = 0

        # Print by file
        for file_name in sorted(by_file.keys()):
            file_profiles = by_file[file_name]
            print(f"{_Color.CYAN}├─ {_Color.WHITE}{file_name}{_Color.RESET}")

            for profile in sorted(file_profiles, key=lambda p: p.name):
                self._print_profile(profile)
                total_time += profile.total_time
                total_memory = max(total_memory, profile.memory_usage)
                total_calls += profile.call_count

            print(f"{_Color.CYAN}└─{_Color.RESET}\n")

        # Print summary
        print(f"{_Color.CYAN}{'─' * 80}{_Color.RESET}")
        print(f"{_Color.CYAN}Summary{_Color.RESET}")
        print(f"{_Color.CYAN}{'─' * 80}{_Color.RESET}")
        print(f"  Functions  {_Color.WHITE}{len(profiles):>10}{_Color.RESET}")
        print(f"  Calls      {_Color.GREEN}{total_calls:>10}{_Color.RESET}")
        print(f"  Time       {_Color.BLUE}{_format_time(total_time):>10}{_Color.RESET}")
        print(f"  Peak Mem   {_Color.RED}{_format_memory(total_memory):>10}{_Color.RESET}")
        print(f"{_Color.CYAN}{'─' * 80}{_Color.RESET}\n")


def print_report(*, show_children: bool = True) -> None:
    """Print profiling report from Registry.

    Args:
        show_children: Whether to display child function calls.
    """
    reporter = Reporter(show_children=show_children)
    reporter.generate_report()
