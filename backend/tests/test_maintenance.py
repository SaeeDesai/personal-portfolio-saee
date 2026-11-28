from unittest.mock import Mock

from backend import maintenance


def test_cleanup_runs_once_per_interval(monkeypatch):
    mock_cleanup = Mock()

    monkeypatch.setattr(maintenance, "cleanup", mock_cleanup)
    monkeypatch.setattr(maintenance, "last_cleanup", None)
    monkeypatch.setattr(maintenance, "monotonic", lambda: 1000)

    maintenance.maybe_cleanup()
    maintenance.maybe_cleanup()

    mock_cleanup.assert_called_once()


def test_cleanup_runs_after_interval(monkeypatch):
    mock_cleanup = Mock()

    monkeypatch.setattr(maintenance, "cleanup", mock_cleanup)
    monkeypatch.setattr(maintenance, "last_cleanup", 1000)
    monkeypatch.setattr(
        maintenance, "monotonic", lambda: 87401
    )

    maintenance.maybe_cleanup()

    mock_cleanup.assert_called_once()