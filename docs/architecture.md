# Architecture

## Pipeline

```
@profile decorator    →    execute_function()    →    generate_report()
   (collect)                 (measure)                  (display)
```

### 1. Collection (`collector.py`)

`@profile` inspects the decorated function:

- Extracts file path and line number via `inspect`.
- Parses the function body with `ast` to find child calls, argument counts, and async status.
- Creates a `FunctionProfile` and stores it in the `Registry`.

### 2. Execution (`executer.py`)

`execute_function()` runs the target in an **isolated subprocess**:

- Uses `multiprocessing` with **spawn** context (no fork) for clean memory measurements.
- Performs a warm-up call first, then a measured call.
- Records wall-clock time (`time.perf_counter`), CPU time (`time.process_time`), and peak memory (`tracemalloc`).
- Sends `ProfileMetrics` back to the parent via a `Queue`.

### 3. Reporting (`reporter.py`)

`generate_report()` reads the `Registry` and prints:

- Functions grouped by source file.
- Metrics per function: calls, total time, CPU time, peak memory.
- Child call details (name, arg count, kwargs, async flag).
- A summary with totals.

### 4. Reset (`resetter.py`)

Two modes:

| Function | Effect |
|----------|--------|
| `reset_metrics()` | Zeros metrics, keeps registrations |
| `reset_all()` | Clears everything |

## Key Design Decisions

- **Subprocess isolation** — Each profiled execution runs in a spawned process so `tracemalloc` measurements are not polluted by the host process.
- **AST-based child detection** — No runtime instrumentation; child calls are discovered statically before execution.
- **Singleton Registry** — All modules share a single `Registry` instance, making the decorator and executor decoupled yet consistent.
- **No external dependencies** — The entire framework uses only the Python standard library.
