"""Command-line interface for pyforge-profile.

Provides CLI for profiling Python modules and generating reports.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

from .main import generate_report, reset_all
from .registry import Registry


def _load_module(file_path: str) -> Any:
    """Load a Python module from file path.

    Args:
        file_path: Path to the Python file to load.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: If file does not exist.
        ImportError: If module cannot be imported.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix != ".py":
        raise ValueError(f"File must be a Python file (.py): {path}")

    # Create a module spec and load the module
    spec = importlib.util.spec_from_file_location("__profiled_module__", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["__profiled_module__"] = module
    spec.loader.exec_module(module)
    return module


def _get_registered_count() -> int:
    """Get count of registered functions."""
    registry = Registry()
    return len(list(registry.all()))


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pyforge-profile",
        description="Profile Python functions with pyforge-profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pyforge_profile script.py
  python -m pyforge_profile --no-children module.py
        """,
    )

    parser.add_argument(
        "file",
        help="Python file to profile (must contain @profile decorated functions)",
    )

    parser.add_argument(
        "--no-children",
        action="store_true",
        help="Hide child function calls in report",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all profiling data after report",
    )

    args = parser.parse_args()

    try:
        # Load the module
        print(f"[CLI] Loading module: {args.file}")
        _load_module(args.file)

        # Check for registered functions
        count = _get_registered_count()
        if count == 0:
            print(f"[CLI] Warning: No functions found with @profile decorator in {args.file}")
            print("[CLI] Generate report anyway? (empty report)")

        print(f"[CLI] Registered {count} functions for profiling\n")

        # Generate report
        show_children = not args.no_children
        generate_report(show_children=show_children)

        # Reset if requested
        if args.reset:
            reset_all()
            print("[CLI] All profiling data reset\n")

    except FileNotFoundError as err:
        print(f"[CLI] Error: {err}", file=sys.stderr)
        sys.exit(1)
    except ValueError as err:
        print(f"[CLI] Error: {err}", file=sys.stderr)
        sys.exit(1)
    except ImportError as err:
        print(f"[CLI] Error importing module: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:  # pylint: disable=broad-except
        print(f"[CLI] Unexpected error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
