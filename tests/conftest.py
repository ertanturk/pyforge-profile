"""Test configuration and fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path so resolve_version can be imported by tests
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
