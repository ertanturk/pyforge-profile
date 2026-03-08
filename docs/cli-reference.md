# CLI Reference

## Usage

```bash
pyforge-profile [options] <file.py>
```

Or via module:

```bash
python -m pyforge_profile [options] <file.py>
```

The target file must contain at least one function decorated with `@profile`.

## Options

| Flag | Description |
|------|-------------|
| `<file.py>` | Python file to profile (required) |
| `--no-children` | Hide child function call details in the report |
| `--reset` | Clear all profiling data after printing the report |
| `--help` | Show help message |

## Examples

Profile a script:

```bash
pyforge-profile app.py
```

Profile without child call details:

```bash
pyforge-profile --no-children app.py
```

Profile and reset afterwards:

```bash
pyforge-profile --reset app.py
```
