pyforge-profile
================================================================================

A lightweight Python profiling framework built from scratch for analyzing
function execution, memory usage, and call patterns. This project is designed
for learning purposes and will be used in personal development projects.

Note: This is not intended as a competitor to existing profiling tools like
cProfile or py-spy, but rather as an educational implementation to understand
profiling mechanics and subprocess management in Python.


Overview
--------------------------------------------------------------------------------

pyforge-profile is a minimal profiling framework that provides:

- Function profiling via @profile decorator
- Isolated subprocess execution for clean measurements
- Memory tracking with tracemalloc
- Child call detection through AST analysis
- Formatted terminal reports
- Command-line and programmatic interfaces


Installation
--------------------------------------------------------------------------------

From source:

    git clone https://github.com/ertanturk/pyforge-profile.git
    cd pyforge-profile
    pip install -e .

From PyPI:

    pip install pyforge-profile


Quick Start
--------------------------------------------------------------------------------

Basic usage with the decorator and CLI:

    from pyforge_profile import profile

    @profile
    def process_data(data):
        total = 0
        for item in data:
            total += item * 2
        return total

    if __name__ == "__main__":
        result = process_data([1, 2, 3, 4, 5])

Run profiling:

    pyforge-profile script.py

Output includes metrics for each profiled function, child calls, and summary
statistics with execution time and memory usage.


Usage
--------------------------------------------------------------------------------

Command Line Interface

    pyforge-profile [options] file.py

    Options:
        --no-children      Hide child function call details
        --reset            Clear profiling data after report
        --help             Show help message

Programmatic API

    from pyforge_profile import (
        profile,
        generate_report,
        reset_metrics,
        execute_function,
    )

    # Mark functions with decorator
    @profile
    def my_function(x):
        return x * 2

    # Execute profiled function in subprocess
    execute_function("my_function", __file__, 10, 42)

    # Generate and print report
    generate_report(show_children=True)

    # Reset metrics for re-profiling
    reset_metrics()


How It Works
--------------------------------------------------------------------------------

Profiling Phases

1. Collection
   Mark functions with @profile decorator. AST analysis detects child calls
   and async status. Function metadata is registered in the Registry singleton.

2. Execution
   Functions are executed in isolated subprocesses using spawn context. This
   ensures accurate memory measurements (no fork contamination) and prevents
   deadlocks from inherited thread state.

3. Measurement
   During execution, metrics are collected: wall-clock time, CPU time, peak
   memory usage via tracemalloc, and call counts.

4. Reporting
   Results are aggregated and displayed in formatted tables with clear section
   organization and readable unit conversions (μs/ms/s, B/KB/MB/GB).

5. Reset
   Metrics can be cleared while preserving registrations (reset_metrics) or
   completely reset including all registrations (reset_all).

Architecture

- collector.py    - @profile decorator with FunctionAnalyzer for AST parsing
- executer.py     - Subprocess management with spawn context
- registry.py     - Singleton function storage and retrieval
- entry.py        - FunctionProfile data class and metrics
- reporter.py     - Formatted output generation (no terminal icons)
- resetter.py     - State management between profiling cycles
- main.py         - Public API surface
- __main__.py     - CLI entry point


Features
--------------------------------------------------------------------------------

Decorator-Based

    @profile
    def my_function():
        pass

Subprocess Isolation

Functions execute in isolated processes with spawn context for accurate
measurements and safe execution.

Child Call Detection

AST parsing detects which child functions are called, including argument
counts, keyword names, and async status.

Memory Profiling

Peak memory usage tracked via tracemalloc. Results shown in human-readable
units (B, KB, MB, GB).

Formatted Reports

Terminal output organized by source file, function, and metrics with clear
section separation.

Dual Reset Modes

- reset_metrics() - Clear measurements, keep registrations
- reset_all() - Complete cleanup for new profiling session

Type Safe

Full type hints throughout codebase. PEP 561 compliant with py.typed marker.


Requirements
--------------------------------------------------------------------------------

Python 3.12 or later

No external dependencies for core functionality.


Quality Standards
--------------------------------------------------------------------------------

Code Quality

- Ruff: All checks passing
- Mypy: Strict mode, 0 errors
- Pylint: 9.98/10 rating
- Bandit: 0 security issues

Coverage

- Type coverage: 100%
- Docstring coverage: 100%
- 9 modules, all type-checked

Configuration

- pyproject.toml: 350+ lines of configuration
- All tools configured for consistent quality standards
- Automated checks via GitHub Actions


Project Status
--------------------------------------------------------------------------------

Development Status: Alpha (0.0.0)

This is a learning project created to understand profiling mechanics,
subprocess management, and AST parsing in Python. It is stable enough for
personal use and experimentation but is not intended for production
profiling of critical systems.

Intended Use

- Educational understanding of profiling concepts
- Personal project development and optimization
- Experimentation with Python internals
- Practice with subprocess management and type safety


Contributing
--------------------------------------------------------------------------------

This is a personal learning project. While contributions are welcome as
collaborative learning exercises, the primary intent is educational rather
than building a production-grade tool.


License
--------------------------------------------------------------------------------

MIT License

See LICENSE file for details.


Author
--------------------------------------------------------------------------------

Ertan Tunç Türk
ertantuncturk61@gmail.com

GitHub: https://github.com/ertanturk/pyforge-profile


References
--------------------------------------------------------------------------------
Python Documentation
- AST module: https://docs.python.org/3/library/ast.html
- multiprocessing: https://docs.python.org/3/library/multiprocessing.html
- tracemalloc: https://docs.python.org/3/library/tracemalloc.html
- inspect module: https://docs.python.org/3/library/inspect.html
