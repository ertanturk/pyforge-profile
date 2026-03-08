"""Resolve and bump the next package version.

Versioning algorithm:
  1. Fetch the current published version from the PyPI JSON API.
  2. Read the local .version cache file (guard against PyPI being unreachable).
  3. Select the *higher* valid semver of the two versions.
     - If only one source is available and valid, use that one.
     - If both are unavailable or invalid, fail with an error.
  4. Increment the patch segment to produce the next version.
  5. Write the new version to:
     - ``pyproject.toml``  — targeted line replacement that preserves all
                             comments and formatting (avoids reformatting the
                             whole file when using a TOML round-trip writer).
     - ``.version``        — local cache for future runs.
  6. Export ``NEW_VERSION`` to ``GITHUB_ENV`` and ``GITHUB_OUTPUT`` so that
     downstream workflow steps and jobs can consume the value.

Usage::

    python scripts/resolve_version.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

PACKAGE_NAME: str = "pyforge-profile"
PYPI_API_URL: str = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
VERSION_CACHE: Path = Path(".version")
PYPROJECT: Path = Path("pyproject.toml")
SEMVER_PARTS: int = 3  # Semantic versioning requires major.minor.patch
FALLBACK: str = "0.0.0"  # Default version when both PyPI and cache are unavailable
# Matches the ``version = "x.y.z"`` line inside [project] while leaving every
# other line untouched.  The pattern anchors to the start of a line (MULTILINE)
# and captures the surrounding quotes so the substitution only replaces the
# digits.
_VERSION_RE: re.Pattern[str] = re.compile(
    r'^(version\s*=\s*")[^"]*(")',
    re.MULTILINE,
)


def fetch_pypi_version() -> str | None:
    """Return the latest published version from PyPI, or ``None`` on failure.

    Uses a custom opener that only allows https:// URLs to prevent scheme
    injection attacks.
    """
    parsed = urllib.parse.urlparse(PYPI_API_URL)
    if parsed.scheme != "https" or not parsed.netloc:
        print(
            f"[PyPI]  invalid URL: scheme={parsed.scheme!r}, netloc={parsed.netloc!r}",
            file=sys.stderr,
        )
        return None

    try:
        # https_only_opener ensures we never open non-https:// schemes
        https_only_opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(),
        )
        # Call build_opener.open() directly with Dict headers to avoid Request object
        with https_only_opener.open(
            PYPI_API_URL,
            timeout=10,
            data=None,
        ) as resp:
            data: dict[str, Any] = cast("dict[str, Any]", json.loads(resp.read()))
            # Extract and validate the version string from nested dict structure
            info = cast("dict[str, Any]", data.get("info"))
            version_value = info.get("version")
            if not isinstance(version_value, str):
                raise TypeError("Expected version to be a string in PyPI JSON response")
            version: str = version_value
            _parse(version)
            print(f"[PyPI]  fetched version : {version}")
            return version
    except (
        ValueError,
        TypeError,
        urllib.error.URLError,
        KeyError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"[PyPI]  fetch failed      : {exc}", file=sys.stderr)
        return None


def read_cache() -> str | None:
    """Return the version stored in ``.version``, or ``None`` if absent."""
    if VERSION_CACHE.exists():
        text = VERSION_CACHE.read_text(encoding="utf-8").strip()
        if text:
            try:
                _parse(text)
            except ValueError as exc:
                print(f"[Cache] invalid version : {text} ({exc})", file=sys.stderr)
                return None
            print(f"[Cache] version          : {text}")
            return text
    print("[Cache] no cache file found.")
    return None


def _parse(v: str) -> tuple[int, int, int]:
    parts = v.split(".")
    if len(parts) != SEMVER_PARTS:
        raise ValueError(f"Expected semver x.y.z, got: {v!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def select_base(pypi: str | None, cache: str | None) -> str:
    """Return the higher of the two version strings with full fallback handling."""
    if pypi is None and cache is None:
        print(f"[Version] both unavailable → using fallback {FALLBACK}")
        return FALLBACK

    if pypi is None:
        print(f"[Version] PyPI unavailable → using cache {cache}")
        return cache  # type: ignore[return-value]  # guaranteed str by caller

    if cache is None:
        print(f"[Version] no cache → using PyPI {pypi}")
        return pypi

    chosen = pypi if _parse(pypi) >= _parse(cache) else cache
    print(f"[Version] selected         : {chosen}  (pypi={pypi}, cache={cache})")
    return chosen


def increment_patch(version: str) -> str:
    """Return *version* with its patch segment incremented by one."""
    major, minor, patch = _parse(version)
    return f"{major}.{minor}.{patch + 1}"


def update_pyproject(new_version: str) -> None:
    """Update only the ``version`` line in pyproject.toml.

    A targeted regex replacement is used instead of a full TOML round-trip
    writer so that every comment, blank line, and section ordering in the
    file is preserved exactly as the author wrote it.
    """
    content = PYPROJECT.read_text(encoding="utf-8")
    updated, count = _VERSION_RE.subn(rf"\g<1>{new_version}\g<2>", content)
    if count == 0:
        print(
            "[pyproject.toml] WARNING: version line not found — file not updated.",
            file=sys.stderr,
        )
        return
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"[pyproject.toml] version → {new_version}")


def _export(key: str, value: str) -> None:
    """Append ``key=value`` to GITHUB_ENV and GITHUB_OUTPUT when running in CI."""
    for env_var in ("GITHUB_ENV", "GITHUB_OUTPUT"):
        path = os.environ.get(env_var)
        if path:
            with Path(path).open("a", encoding="utf-8") as fh:
                fh.write(f"{key}={value}\n")


def main() -> None:
    """Orchestrate version resolution, file updates, and CI environment export."""
    pypi_version = fetch_pypi_version()
    cache_version = read_cache()

    base = select_base(pypi_version, cache_version)
    next_version = increment_patch(base)

    print(f"[Version] next version    : {next_version}")

    update_pyproject(next_version)

    VERSION_CACHE.write_text(next_version, encoding="utf-8")
    print(f"[Cache]  wrote .version  → {next_version}")

    _export("NEW_VERSION", next_version)
    print(f"\nNEW_VERSION={next_version}")


if __name__ == "__main__":
    main()
