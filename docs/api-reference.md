# API Reference

All public symbols are available from `pyforge_profile`:

```python
from pyforge_profile import (
    profile,
    execute_function,
    generate_report,
    reset_metrics,
    reset_all,
    get_registry,
)
```

---

## `@profile`

Decorator that registers a function for profiling.

```python
@profile
def my_func(x: int) -> int:
    return x * 2
```

- Validates the target is callable.
- Detects sync/async automatically.
- Parses the function body with AST to discover child calls.
- Registers a `FunctionProfile` entry in the global `Registry`.

Works with both sync and `async` functions.

---

## `execute_function`

```python
execute_function(
    func_name: str,
    file_name: str,
    line_number: int,
    *args,
    timeout: float = 60.0,
    **kwargs,
) -> None
```

Runs a registered function in an **isolated subprocess** (spawn context) and records metrics.

| Parameter | Description |
|-----------|-------------|
| `func_name` | Name of the decorated function |
| `file_name` | Source file path (use `__file__`) |
| `line_number` | Line where the function is defined |
| `*args / **kwargs` | Arguments forwarded to the function |
| `timeout` | Max seconds before the subprocess is killed (default 60) |

**Raises:** `ValueError`, `SerializationError`, `SubprocessTimeoutError`, `SubprocessCrashError`

---

## `generate_report`

```python
generate_report(*, show_children: bool = True) -> None
```

Prints a formatted profiling report to the terminal, grouped by file.

Set `show_children=False` to hide child-call details.

---

## `reset_metrics`

```python
reset_metrics() -> None
```

Zeros out `call_count`, `total_time`, `self_time`, and `memory_usage` for every registered function **without** removing them from the registry.

Use this between profiling runs on the same set of functions.

---

## `reset_all`

```python
reset_all() -> None
```

Clears the entire registry — removes all function registrations and their data.

---

## `get_registry`

```python
get_registry() -> Registry
```

Returns the global `Registry` singleton. Useful for inspecting registered profiles directly:

```python
registry = get_registry()
for fp in registry.all():
    print(fp.name, fp.total_time)
```
