"""Tests for CMD-002 IndexIncremental command."""

import subprocess
from pathlib import Path

import pytest

from kdd.application.commands.index_incremental import (
    IncrementalResult,
    index_incremental,
)
from kdd.application.extractors.registry import create_default_registry
from kdd.domain.entities import IndexManifest, IndexStats
from kdd.domain.enums import IndexLevel
from kdd.infrastructure.artifact.filesystem import FilesystemArtifactStore


@pytest.fixture
def git_specs(tmp_path):
    """Create a temporary git repo with a few spec files."""
    specs = tmp_path / "specs"
    specs.mkdir()

    # Init git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True,
    )

    # Create directory structure
    domain = specs / "01-domain" / "entities"
    domain.mkdir(parents=True)

    # Create a spec file
    entity = domain / "Order.md"
    entity.write_text(
        "---\nid: Order\nkind: entity\nstatus: draft\n---\n\n"
        "# Order\n\n## Descripción\n\nAn order entity.\n"
    )

    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, capture_output=True,
    )

    return specs


@pytest.fixture
def artifact_store(tmp_path):
    return FilesystemArtifactStore(tmp_path / ".kdd-index")


@pytest.fixture
def registry():
    return create_default_registry()


class TestFullReindex:
    """No previous manifest → full reindex."""

    def test_indexes_all_files(self, git_specs, artifact_store, registry):
        result = index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.is_full_reindex is True
        assert result.indexed >= 1

    def test_creates_manifest(self, git_specs, artifact_store, registry):
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        manifest = artifact_store.read_manifest()
        assert manifest is not None
        assert manifest.git_commit is not None
        assert manifest.stats.nodes >= 1

    def test_creates_node(self, git_specs, artifact_store, registry):
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        node = artifact_store.read_node("Entity:Order")
        assert node is not None


class TestIncrementalNew:
    """New file added since last index."""

    def test_indexes_new_file(self, git_specs, artifact_store, registry):
        # First: full index
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )

        # Add a new file and commit
        events_dir = git_specs / "01-domain" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        evt = events_dir / "EVT-Order-Created.md"
        evt.write_text(
            "---\nid: EVT-Order-Created\nkind: event\nstatus: draft\n---\n\n"
            "# EVT-Order-Created\n\n## Descripción\n\nOrder was created.\n"
        )
        subprocess.run(["git", "add", "."], cwd=git_specs.parent, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add event"],
            cwd=git_specs.parent, capture_output=True,
        )

        # Incremental
        result = index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.is_full_reindex is False
        assert result.indexed >= 1

        # Verify new node exists
        node = artifact_store.read_node("Event:EVT-Order-Created")
        assert node is not None


class TestIncrementalModified:
    """Modified file since last index."""

    def test_reindexes_modified_file(self, git_specs, artifact_store, registry):
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )

        # Modify the entity file
        entity = git_specs / "01-domain" / "entities" / "Order.md"
        entity.write_text(
            "---\nid: Order\nkind: entity\nstatus: review\n---\n\n"
            "# Order\n\n## Descripción\n\nAn order entity (updated).\n"
        )
        subprocess.run(["git", "add", "."], cwd=git_specs.parent, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "update order"],
            cwd=git_specs.parent, capture_output=True,
        )

        result = index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.indexed >= 1

        # Verify updated node
        node = artifact_store.read_node("Entity:Order")
        assert node is not None
        assert node.status == "review"


class TestIncrementalDeleted:
    """Deleted file since last index."""

    def test_cascade_deletes(self, git_specs, artifact_store, registry):
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )

        # Delete the entity file
        entity = git_specs / "01-domain" / "entities" / "Order.md"
        entity.unlink()
        subprocess.run(["git", "add", "."], cwd=git_specs.parent, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "delete order"],
            cwd=git_specs.parent, capture_output=True,
        )

        result = index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.deleted >= 1


class TestIncrementalNoChanges:
    """No changes since last index."""

    def test_noop(self, git_specs, artifact_store, registry):
        index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )

        result = index_incremental(
            git_specs,
            repo_root=git_specs.parent,
            registry=registry,
            artifact_store=artifact_store,
        )
        assert result.is_full_reindex is False
        assert result.indexed == 0
        assert result.deleted == 0
