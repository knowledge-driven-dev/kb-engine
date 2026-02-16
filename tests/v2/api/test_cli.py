"""Tests for the kdd CLI (Click commands)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kdd.api.cli import cli
from kdd.domain.entities import IndexManifest, IndexStats
from kdd.domain.enums import IndexLevel


@pytest.fixture
def runner():
    return CliRunner()


class TestCliVersion:
    def test_version_flag(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "kdd" in result.output
        assert "1.0.0" in result.output


class TestCliStatus:
    def test_status_no_index(self, runner, tmp_path):
        result = runner.invoke(cli, ["status", "--specs-path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No index found" in result.output

    def test_status_with_index(self, runner, tmp_path):
        # Create a minimal .kdd-index/ with manifest
        from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore

        idx_path = tmp_path / ".kdd-index"
        store = FilesystemArtifactStore(idx_path)
        store.write_manifest(IndexManifest(
            version="1.0.0",
            kdd_version="1.0.0",
            indexed_at=datetime(2025, 1, 15),
            indexed_by="test",
            index_level=IndexLevel.L1,
            stats=IndexStats(nodes=10, edges=20, embeddings=0),
        ))

        # specs_path is a dir; index_path is parent/.kdd-index
        specs = tmp_path / "specs"
        specs.mkdir()

        result = runner.invoke(cli, [
            "status", "--specs-path", str(specs), "--index-path", str(idx_path),
        ])
        assert result.exit_code == 0
        assert "Nodes:" in result.output
        assert "10" in result.output


class TestCliIndex:
    def test_index_nonexistent_path(self, runner):
        result = runner.invoke(cli, ["index", "/nonexistent/path"])
        assert result.exit_code != 0

    @patch("kdd.api.cli.create_container")
    def test_index_invokes_incremental(self, mock_create, runner, tmp_path):
        """Verify that 'kdd index <path>' calls index_incremental."""
        # Create specs directory
        specs = tmp_path / "specs"
        specs.mkdir()

        mock_container = MagicMock()
        mock_container.index_level.value = "L1"
        mock_container.index_path = str(tmp_path / ".kdd-index")
        mock_create.return_value = mock_container

        with patch("kdd.application.commands.index_incremental.index_incremental") as mock_idx:
            from dataclasses import dataclass

            @dataclass
            class FakeResult:
                indexed: int = 5
                deleted: int = 0
                skipped: int = 0
                errors: int = 0
                is_full_reindex: bool = False

            mock_idx.return_value = FakeResult()

            result = runner.invoke(cli, ["index", str(specs)])

        assert result.exit_code == 0
        assert "Indexed: 5" in result.output


class TestCliSearch:
    @patch("kdd.api.cli.create_container")
    def test_search_no_index(self, mock_create, runner, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()

        mock_container = MagicMock()
        mock_container.ensure_loaded.return_value = False
        mock_create.return_value = mock_container

        result = runner.invoke(cli, [
            "search", "test query", "--specs-path", str(specs),
        ])
        assert result.exit_code != 0
        assert "No index found" in result.output


class TestCliMerge:
    def test_merge_missing_sources(self, runner, tmp_path):
        src1 = tmp_path / "idx1"
        src2 = tmp_path / "idx2"
        out = tmp_path / "out"

        src1.mkdir()
        src2.mkdir()

        result = runner.invoke(cli, [
            "merge", str(src1), str(src2), "-o", str(out),
        ])
        # Should fail because no manifests
        assert result.exit_code != 0 or "failed" in result.output.lower()
