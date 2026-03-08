# Getting Started

## Installation

From PyPI:

```bash
pip install pyforge-profile
```

From source:

```bash
git clone https://github.com/ertanturk/pyforge-profile.git
cd pyforge-profile
pip install -e .
```

**Requires Python 3.12+.** No external dependencies.

## Quick Example

Create a file `demo.py`:

```python
from pyforge_profile import profile, execute_function, generate_report

@profile
def compute(n: int) -> int:
    """Sum of squares up to n."""
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    # Execute in an isolated subprocess for accurate measurements
    execute_function("compute", __file__, 4, 10_000)

    # Print a formatted report
    generate_report()
```

Run it:

```bash
python demo.py
```

Or use the CLI directly:

```bash
pyforge-profile demo.py
```

## What You Get

The report shows, for each `@profile`-decorated function:

| Metric | Description |
|--------|-------------|
| **calls** | Number of times the function was executed |
| **total** | Wall-clock time (includes children) |
| **cpu** | CPU time (excludes I/O wait) |
| **mem** | Peak memory usage via `tracemalloc` |
| **child calls** | Functions called inside the body (via AST) |
