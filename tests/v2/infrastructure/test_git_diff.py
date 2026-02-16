"""Tests for kdd.infrastructure.git.diff."""

import subprocess
from pathlib import Path

import pytest

from kdd.infrastructure.git.diff import (
    DiffResult,
    get_current_commit,
    get_diff,
    is_git_repo,
    scan_files,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a minimal git repository for testing."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )

    # Create initial files
    specs = tmp_path / "specs" / "01-domain" / "entities"
    specs.mkdir(parents=True)
    (specs / "Pedido.md").write_text("---\nkind: entity\n---\n# Pedido\n")
    (specs / "Usuario.md").write_text("---\nkind: entity\n---\n# Usuario\n")
    (tmp_path / "README.md").write_text("# Project\n")

    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


class TestIsGitRepo:
    def test_valid_repo(self, git_repo):
        assert is_git_repo(git_repo) is True

    def test_not_a_repo(self, tmp_path):
        assert is_git_repo(tmp_path) is False


class TestGetCurrentCommit:
    def test_returns_hash(self, git_repo):
        commit = get_current_commit(git_repo)
        assert commit is not None
        assert len(commit) == 40  # full SHA

    def test_not_a_repo(self, tmp_path):
        assert get_current_commit(tmp_path) is None


class TestScanFiles:
    def test_all_files(self, git_repo):
        files = scan_files(git_repo)
        assert "README.md" in files
        assert "specs/01-domain/entities/Pedido.md" in files

    def test_with_pattern(self, git_repo):
        files = scan_files(git_repo, include_patterns=["specs/**/*.md"])
        assert "README.md" not in files
        assert "specs/01-domain/entities/Pedido.md" in files
        assert len(files) == 2


class TestGetDiff:
    def test_detect_added_file(self, git_repo):
        base = get_current_commit(git_repo)

        # Add a new file
        new_file = git_repo / "specs" / "01-domain" / "entities" / "Nuevo.md"
        new_file.write_text("---\nkind: entity\n---\n# Nuevo\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "add"],
            cwd=git_repo, capture_output=True, check=True,
        )

        diff = get_diff(git_repo, base)
        assert "specs/01-domain/entities/Nuevo.md" in diff.added
        assert diff.deleted == []

    def test_detect_modified_file(self, git_repo):
        base = get_current_commit(git_repo)

        # Modify existing file
        pedido = git_repo / "specs" / "01-domain" / "entities" / "Pedido.md"
        pedido.write_text("---\nkind: entity\n---\n# Pedido\n\nModified.\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "modify"],
            cwd=git_repo, capture_output=True, check=True,
        )

        diff = get_diff(git_repo, base)
        assert "specs/01-domain/entities/Pedido.md" in diff.modified

    def test_detect_deleted_file(self, git_repo):
        base = get_current_commit(git_repo)

        # Delete a file
        (git_repo / "specs" / "01-domain" / "entities" / "Usuario.md").unlink()
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "delete"],
            cwd=git_repo, capture_output=True, check=True,
        )

        diff = get_diff(git_repo, base)
        assert "specs/01-domain/entities/Usuario.md" in diff.deleted

    def test_with_include_pattern(self, git_repo):
        base = get_current_commit(git_repo)

        # Add files in and out of pattern
        (git_repo / "README.md").write_text("# Modified\n")
        new_spec = git_repo / "specs" / "01-domain" / "entities" / "Nuevo.md"
        new_spec.write_text("---\nkind: entity\n---\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "mixed"],
            cwd=git_repo, capture_output=True, check=True,
        )

        diff = get_diff(git_repo, base, include_patterns=["specs/**/*.md"])
        all_files = diff.added + diff.modified + diff.deleted
        assert all("specs/" in f for f in all_files)

    def test_no_changes(self, git_repo):
        base = get_current_commit(git_repo)
        diff = get_diff(git_repo, base)
        assert diff.added == []
        assert diff.modified == []
        assert diff.deleted == []
