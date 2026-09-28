"""Tests for batch PR scanning functionality."""

from smart_pr_review_workflow.batch import (
    BatchScanConfig,
    PRBatchItem,
)


def test_batch_scan_config_creation():
    """Test BatchScanConfig is properly initialized."""
    config = BatchScanConfig(
        owner="test-owner",
        repo="test-repo",
        labels=["type:dependency"],
        max_results=20,
        state="closed",
    )
    assert config.owner == "test-owner"
    assert config.repo == "test-repo"
    assert config.labels == ["type:dependency"]
    assert config.max_results == 20
    assert config.state == "closed"
    assert config.exclude_draft is True


def test_batch_scan_config_defaults():
    """Test BatchScanConfig defaults."""
    config = BatchScanConfig(
        owner="owner",
        repo="repo",
    )
    assert config.state == "open"
    assert config.sort == "created"
    assert config.direction == "desc"
    assert config.max_results == 10
    assert config.exclude_draft is True
    assert config.labels is None
    assert config.exclude_labels is None


def test_pr_batch_item_creation():
    """Test PRBatchItem is properly initialized."""
    item = PRBatchItem(
        owner="owner",
        repo="repo",
        number=42,
        title="Fix: something",
        url="https://github.com/owner/repo/pull/42",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        is_draft=False,
    )
    assert item.owner == "owner"
    assert item.repo == "repo"
    assert item.number == 42
    assert item.title == "Fix: something"
    assert item.is_draft is False


def test_batch_config_exclude_labels_filter():
    """Test exclude_labels configuration."""
    config = BatchScanConfig(
        owner="owner",
        repo="repo",
        exclude_labels=["wip", "hold"],
    )
    assert config.exclude_labels == ["wip", "hold"]


def test_batch_config_multiple_labels():
    """Test multiple labels in filter."""
    config = BatchScanConfig(
        owner="owner",
        repo="repo",
        labels=["type:security", "type:dependency", "priority:high"],
    )
    assert len(config.labels) == 3
    assert "type:security" in config.labels
