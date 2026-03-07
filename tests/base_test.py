"""Base critical tests"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import pytest
from resolve_version import (
    FALLBACK,
    SEMVER_PARTS,
    _parse,  # type: ignore
    increment_patch,
    read_cache,
    select_base,
)


class TestVersionParsing:
    """Test semantic version parsing and validation."""

    def test_parse_valid_semver(self) -> None:
        """Valid x.y.z version should parse correctly."""
        major, minor, patch = _parse("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3

    def test_parse_invalid_semver_too_few_parts(self) -> None:
        """Version with fewer than 3 parts should raise ValueError."""
        with pytest.raises(ValueError, match=r"Expected semver x\.y\.z"):
            _parse("1.2")

    def test_parse_invalid_semver_too_many_parts(self) -> None:
        """Version with more than 3 parts should raise ValueError."""
        with pytest.raises(ValueError, match=r"Expected semver x\.y\.z"):
            _parse("1.2.3.4")

    def test_parse_invalid_semver_non_numeric(self) -> None:
        """Version with non-numeric parts should raise ValueError."""
        with pytest.raises(ValueError, match="invalid literal for int"):
            _parse("a.b.c")


class TestVersionIncrement:
    """Test patch version incrementing."""

    def test_increment_patch_basic(self) -> None:
        """Incrementing 1.2.3 should produce 1.2.4."""
        assert increment_patch("1.2.3") == "1.2.4"

    def test_increment_patch_from_zero(self) -> None:
        """Incrementing 0.0.0 should produce 0.0.1."""
        assert increment_patch("0.0.0") == "0.0.1"

    def test_increment_patch_large_number(self) -> None:
        """Incrementing patch with large numbers should work."""
        assert increment_patch("2.5.999") == "2.5.1000"


class TestVersionSelection:
    """Test version selection logic with fallbacks."""

    def test_select_both_none_returns_fallback(self) -> None:
        """When both sources are None, should return FALLBACK (0.0.0)."""
        result = select_base(None, None)
        assert result == FALLBACK

    def test_select_pypi_none_uses_cache(self) -> None:
        """When PyPI is None but cache exists, use cache."""
        result = select_base(None, "1.0.0")
        assert result == "1.0.0"

    def test_select_cache_none_uses_pypi(self) -> None:
        """When cache is None but PyPI exists, use PyPI."""
        result = select_base("2.0.0", None)
        assert result == "2.0.0"

    def test_select_higher_version_from_multiple(self) -> None:
        """When both exist, should select the higher version."""
        result = select_base("1.5.0", "1.4.9")
        assert result == "1.5.0"

    def test_select_cache_higher_than_pypi(self) -> None:
        """When cache is higher than PyPI, select cache."""
        result = select_base("1.2.0", "1.3.0")
        assert result == "1.3.0"


class TestCacheReading:
    """Test reading version from cache file."""

    def test_read_cache_file_exists(self) -> None:
        """Should read version from existing .version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".version"
            cache_file.write_text("2.1.0", encoding="utf-8")

            with mock.patch("resolve_version.VERSION_CACHE", cache_file):
                result = read_cache()
                assert result == "2.1.0"

    def test_read_cache_file_not_found(self) -> None:
        """Should return None when cache file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".version"

            with mock.patch("resolve_version.VERSION_CACHE", cache_file):
                result = read_cache()
                assert result is None

    def test_read_cache_file_empty(self) -> None:
        """Should return None when cache file is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".version"
            cache_file.write_text("", encoding="utf-8")

            with mock.patch("resolve_version.VERSION_CACHE", cache_file):
                result = read_cache()
                assert result is None


class TestConstants:
    """Test module constants."""

    def test_semver_parts_constant(self) -> None:
        """SEMVER_PARTS should be 3 for major.minor.patch."""
        assert SEMVER_PARTS == 3

    def test_fallback_constant(self) -> None:
        """FALLBACK should be 0.0.0."""
        assert FALLBACK == "0.0.0"
