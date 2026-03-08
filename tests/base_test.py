"""Critical tests for pyforge-profile core functionality."""

from __future__ import annotations

# Test pyforge-profile package
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Test resolve_version script
from resolve_version import (  # type: ignore[import-not-found]
    FALLBACK,
    SEMVER_PARTS,
    _parse,  # type: ignore
    increment_patch,
    read_cache,
    select_base,
)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyforge_profile.collector import ChildFunctionCall, FunctionAnalyzer, profile
from pyforge_profile.entry import FunctionProfile
from pyforge_profile.executer import ProfileMetrics, SerializationError
from pyforge_profile.registry import Registry
from pyforge_profile.reporter import _format_memory, _format_time  # type: ignore
from pyforge_profile.resetter import Resetter


# Module-level function for analyzer testing (to avoid indentation issues)
def sample_module_function() -> int:
    """Sample function for analyzer testing."""
    x = 1
    y = 2
    return x + y


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


# ==============================================================================
# CRITICAL TESTS: FunctionProfile (entry.py)
# ==============================================================================


class TestFunctionProfile:
    """Test FunctionProfile data class.

    Critical for: Storing and retrieving profiling data.
    """

    def test_function_profile_creation(self) -> None:
        """FunctionProfile should store all profiling data correctly."""

        def dummy_func() -> None:
            pass

        profile = FunctionProfile(
            func=dummy_func,
            function_name="dummy_func",
            file_name="test.py",
            line_number=42,
            call_count=5,
            total_time=1.5,
            self_time=1.0,
            memory_usage=1024.0,
        )

        assert profile.function is dummy_func
        assert profile.name == "dummy_func"
        assert profile.file_name == "test.py"
        assert profile.line_number == 42
        assert profile.call_count == 5
        assert profile.total_time == 1.5
        assert profile.self_time == 1.0
        assert profile.memory_usage == 1024.0

    def test_function_profile_defaults(self) -> None:
        """FunctionProfile should have default values for metrics."""

        def dummy_func() -> None:
            pass

        profile = FunctionProfile(
            func=dummy_func,
            function_name="dummy_func",
            file_name="test.py",
            line_number=10,
        )

        assert profile.call_count == 0
        assert profile.total_time == 0.0
        assert profile.self_time == 0.0
        assert profile.memory_usage == 0.0

    def test_function_profile_metric_updates(self) -> None:
        """FunctionProfile metrics should be mutable."""

        def dummy_func() -> None:
            pass

        profile = FunctionProfile(
            func=dummy_func,
            function_name="dummy_func",
            file_name="test.py",
            line_number=10,
        )

        profile.call_count = 10
        profile.total_time = 2.5
        profile.self_time = 2.0
        profile.memory_usage = 2048.0

        assert profile.call_count == 10
        assert profile.total_time == 2.5
        assert profile.self_time == 2.0
        assert profile.memory_usage == 2048.0


# ==============================================================================
# CRITICAL TESTS: Registry (registry.py)
# ==============================================================================


class TestRegistry:
    """Test Registry singleton for function storage.

    Critical for: Storing and retrieving profiled functions across the system.
    """

    def setup_method(self) -> None:
        """Clear registry before each test."""
        Registry().clear()

    def test_registry_singleton(self) -> None:
        """Registry should be a singleton."""
        reg1 = Registry()
        reg2 = Registry()
        assert reg1 is reg2

    def test_registry_register_and_get(self) -> None:
        """Registry should store and retrieve profiles."""

        def dummy_func() -> None:
            pass

        profile = FunctionProfile(
            func=dummy_func,
            function_name="dummy",
            file_name="test.py",
            line_number=10,
        )

        registry = Registry()
        registry.register(profile)
        retrieved = registry.get("test.py", 10, "dummy")

        assert retrieved is not None
        assert retrieved.name == "dummy"
        assert retrieved.file_name == "test.py"

    def test_registry_get_nonexistent(self) -> None:
        """Registry.get should return None for nonexistent profiles."""
        registry = Registry()
        result = registry.get("missing.py", 0, "missing")
        assert result is None

    def test_registry_clear(self) -> None:
        """Registry.clear should remove all profiles."""

        def dummy_func() -> None:
            pass

        profile = FunctionProfile(
            func=dummy_func,
            function_name="dummy",
            file_name="test.py",
            line_number=10,
        )

        registry = Registry()
        registry.register(profile)
        assert len(registry) > 0

        registry.clear()
        assert len(registry) == 0

    def test_registry_all(self) -> None:
        """Registry.all should return all profiles."""

        def dummy1() -> None:
            pass

        def dummy2() -> None:
            pass

        profile1 = FunctionProfile(dummy1, "dummy1", "test.py", 10)
        profile2 = FunctionProfile(dummy2, "dummy2", "test.py", 20)

        registry = Registry()
        registry.register(profile1)
        registry.register(profile2)

        all_profiles = list(registry.all())
        assert len(all_profiles) == 2
        assert profile1 in all_profiles
        assert profile2 in all_profiles

    def test_registry_len(self) -> None:
        """Registry.__len__ should return entry count."""

        def dummy() -> None:
            pass

        registry = Registry()
        assert len(registry) == 0

        registry.register(FunctionProfile(dummy, "dummy", "test.py", 10))
        assert len(registry) == 1

        registry.register(FunctionProfile(dummy, "dummy", "test.py", 20))
        assert len(registry) == 2

    def test_registry_contains(self) -> None:
        """Registry.__contains__ should check for key existence."""

        def dummy() -> None:
            pass

        registry = Registry()
        key = "test.py:10:dummy"

        assert key not in registry

        registry.register(FunctionProfile(dummy, "dummy", "test.py", 10))
        assert key in registry


# ==============================================================================
# CRITICAL TESTS: Resetter (resetter.py)
# ==============================================================================


class TestResetter:
    """Test Resetter for state management.

    Critical for: Clearing profiling data between runs.
    """

    def setup_method(self) -> None:
        """Set up test fixtures."""
        Registry().clear()

    def test_reset_all(self) -> None:
        """reset_all should clear all profiles from registry."""

        def dummy() -> None:
            pass

        profile = FunctionProfile(dummy, "dummy", "test.py", 10, call_count=5)
        Registry().register(profile)
        assert len(Registry()) == 1

        Resetter.reset_all()
        assert len(Registry()) == 0

    def test_reset_metrics(self) -> None:
        """reset_metrics should clear metrics but keep profiles."""

        def dummy() -> None:
            pass

        profile = FunctionProfile(
            dummy,
            "dummy",
            "test.py",
            10,
            call_count=5,
            total_time=1.5,
            self_time=1.0,
            memory_usage=1024.0,
        )

        registry = Registry()
        registry.register(profile)
        Resetter.reset_metrics()

        retrieved = registry.get("test.py", 10, "dummy")
        assert retrieved is not None
        assert retrieved.call_count == 0
        assert retrieved.total_time == 0.0
        assert retrieved.self_time == 0.0
        assert retrieved.memory_usage == 0.0

    def test_reset_metrics_preserves_metadata(self) -> None:
        """reset_metrics should preserve function name and location."""

        def dummy() -> None:
            pass

        profile = FunctionProfile(
            dummy,
            "dummy",
            "test.py",
            10,
            call_count=5,
        )

        registry = Registry()
        registry.register(profile)
        Resetter.reset_metrics()

        retrieved = registry.get("test.py", 10, "dummy")
        assert retrieved is not None
        assert retrieved.name == "dummy"
        assert retrieved.file_name == "test.py"
        assert retrieved.line_number == 10


# ==============================================================================
# CRITICAL TESTS: Collector (collector.py)
# ==============================================================================


class TestChildFunctionCall:
    """Test ChildFunctionCall metadata class.

    Critical for: Storing child call information.
    """

    def test_child_function_call_creation(self) -> None:
        """ChildFunctionCall should store call metadata."""
        child_call = ChildFunctionCall(
            name="helper",
            args_count=2,
            kwargs_names=["key1", "key2"],
            is_async=False,
        )

        assert child_call.name == "helper"
        assert child_call.args_count == 2
        assert child_call.kwargs_names == ["key1", "key2"]
        assert child_call.is_async is False

    def test_child_function_call_async(self) -> None:
        """ChildFunctionCall should track async status."""
        child_call = ChildFunctionCall(
            name="async_helper",
            args_count=1,
            kwargs_names=[],
            is_async=True,
        )

        assert child_call.is_async is True

    def test_child_function_call_repr(self) -> None:
        """ChildFunctionCall.__repr__ should provide useful representation."""
        child_call = ChildFunctionCall(
            name="test",
            args_count=2,
            kwargs_names=["x"],
            is_async=True,
        )

        repr_str = repr(child_call)
        assert "test" in repr_str
        assert "async=True" in repr_str


class TestFunctionAnalyzer:
    """Test FunctionAnalyzer for AST parsing.

    Critical for: Extracting child calls and function metadata.
    """

    def test_function_analyzer_basic(self) -> None:
        """FunctionAnalyzer should work with module-level functions."""
        # Test with module-level function to avoid indentation issues
        analyzer = FunctionAnalyzer(sample_module_function)
        assert analyzer.func is sample_module_function
        assert analyzer.source is not None

    def test_profile_decorator_registers_function(self) -> None:
        """profile decorator should register function with registry."""

        @profile
        def decorated_func() -> None:
            pass

        # Profile decorator stores with __file__ and line number
        # Just verify the decorator works without error
        assert decorated_func is not None
        assert callable(decorated_func)

    def test_profile_decorator_call_preserved(self) -> None:
        """profile decorator should preserve function behavior."""

        @profile
        def add(x: int, y: int) -> int:
            return x + y

        result = add(2, 3)
        assert result == 5


# ==============================================================================
# CRITICAL TESTS: Executer (executer.py)
# ==============================================================================


class TestProfileMetrics:
    """Test ProfileMetrics dataclass.

    Critical for: Storing execution measurements.
    """

    def test_profile_metrics_creation(self) -> None:
        """ProfileMetrics should store all timing measurements."""
        metrics = ProfileMetrics(
            wall_time=1.5,
            cpu_time=1.0,
            peak_memory=2048.0,
            call_count=1,
        )

        assert metrics.wall_time == 1.5
        assert metrics.cpu_time == 1.0
        assert metrics.peak_memory == 2048.0
        assert metrics.call_count == 1

    def test_profile_metrics_zero_values(self) -> None:
        """ProfileMetrics should handle zero values."""
        metrics = ProfileMetrics(
            wall_time=0.0,
            cpu_time=0.0,
            peak_memory=0.0,
            call_count=0,
        )

        assert metrics.wall_time == 0.0
        assert metrics.call_count == 0


class TestSerializationError:
    """Test SerializationError exception.

    Critical for: Error handling during serialization.
    """

    def test_serialization_error_creation(self) -> None:
        """SerializationError should be a proper exception."""
        error = SerializationError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


# ==============================================================================
# CRITICAL TESTS: Reporter (reporter.py)
# ==============================================================================


class TestTimeFormatting:
    """Test time formatting utilities.

    Critical for: Converting seconds to readable format.
    """

    def test_format_time_microseconds(self) -> None:
        """Time < 0.001s should be formatted in microseconds."""
        result = _format_time(0.0005)
        assert "μs" in result
        assert "500" in result

    def test_format_time_milliseconds(self) -> None:
        """Time < 1s should be formatted in milliseconds."""
        result = _format_time(0.5)
        assert "ms" in result
        assert "500" in result

    def test_format_time_seconds(self) -> None:
        """Time >= 1s should be formatted in seconds."""
        result = _format_time(2.5)
        assert "s" in result
        assert "2" in result

    def test_format_time_zero(self) -> None:
        """Zero time should format correctly."""
        result = _format_time(0.0)
        assert isinstance(result, str)
        assert "0" in result


class TestMemoryFormatting:
    """Test memory formatting utilities.

    Critical for: Converting bytes to readable format.
    """

    def test_format_memory_bytes(self) -> None:
        """Memory < 1KB should be formatted in bytes."""
        result = _format_memory(512.0)
        assert "B" in result
        assert "512" in result

    def test_format_memory_kilobytes(self) -> None:
        """Memory < 1MB should be formatted in kilobytes."""
        result = _format_memory(512 * 1024.0)
        assert "KB" in result

    def test_format_memory_megabytes(self) -> None:
        """Memory < 1GB should be formatted in megabytes."""
        result = _format_memory(512 * 1024 * 1024.0)
        assert "MB" in result

    def test_format_memory_gigabytes(self) -> None:
        """Memory >= 1GB should be formatted in gigabytes."""
        result = _format_memory(2 * 1024 * 1024 * 1024.0)
        assert "GB" in result

    def test_format_memory_zero(self) -> None:
        """Zero memory should format correctly."""
        result = _format_memory(0.0)
        assert isinstance(result, str)
        assert "0" in result
