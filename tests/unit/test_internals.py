"""Unit tests for the optimizer-internals artifact directory helpers."""

import logging

from aquacal.io import INTERNALS_DIRNAME, ensure_internals_dir, warn_if_overwriting


class TestEnsureInternalsDir:
    """Tests for ensure_internals_dir."""

    def test_ensure_internals_dir_creates(self, tmp_path):
        """Should create internals/ under a tmp_path that doesn't have it yet."""
        result = ensure_internals_dir(tmp_path)

        assert result.exists()
        assert result.is_dir()
        assert result.name == "internals"

    def test_ensure_internals_dir_idempotent(self, tmp_path):
        """Calling twice should not raise and should return the same path."""
        first = ensure_internals_dir(tmp_path)
        second = ensure_internals_dir(tmp_path)

        assert first == second
        assert second.exists()


class TestWarnIfOverwriting:
    """Tests for warn_if_overwriting."""

    def test_warn_if_overwriting_silent_when_absent(self, tmp_path, caplog):
        """Should not log anything for a nonexistent path."""
        missing = tmp_path / "does_not_exist.json"

        with caplog.at_level(logging.WARNING):
            warn_if_overwriting(missing)

        assert caplog.records == []

    def test_warn_if_overwriting_warns_when_present(self, tmp_path, caplog):
        """Should log a warning naming the file when it already exists."""
        existing = tmp_path / "calibration_stage3.json"
        existing.touch()

        with caplog.at_level(logging.WARNING):
            warn_if_overwriting(existing)

        assert len(caplog.records) == 1
        assert "calibration_stage3.json" in caplog.records[0].getMessage()


class TestInternalsDirName:
    """Guard against internals/ colliding with the diagnostics.json name."""

    def test_internals_dir_name_is_not_diagnostics(self):
        """INTERNALS_DIRNAME must stay 'internals', distinct from diagnostics.json."""
        assert INTERNALS_DIRNAME == "internals"
