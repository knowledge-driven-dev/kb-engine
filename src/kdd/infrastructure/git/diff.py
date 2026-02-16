"""Simplified git diff adapter for incremental indexing.

Decoupled from ``RepositoryConfig`` — operates on plain ``Path`` + pattern
lists.  Ported and simplified from ``kb_engine/git/scanner.py``.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffResult:
    """Files changed between two git states."""

    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)


def _run_git(repo: Path, *args: str) -> str:
    """Run a git command in *repo* and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def is_git_repo(repo: Path) -> bool:
    """Return True if *repo* is inside a git working tree."""
    try:
        _run_git(repo, "rev-parse", "--git-dir")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        return False


def get_current_commit(repo: Path) -> str | None:
    """Return the current HEAD commit hash, or None."""
    try:
        return _run_git(repo, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_diff(
    repo: Path,
    since_commit: str,
    *,
    include_patterns: list[str] | None = None,
) -> DiffResult:
    """Return files added/modified/deleted since *since_commit*.

    If *include_patterns* is given, only files matching at least one glob
    pattern are included.
    """
    try:
        output = _run_git(
            repo, "diff", "--name-status", since_commit, "HEAD",
        )
    except subprocess.CalledProcessError:
        return DiffResult()

    result = DiffResult()
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, filepath = parts[0].strip(), parts[1].strip()

        if include_patterns and not _matches_any(filepath, include_patterns):
            continue

        if status.startswith("A"):
            result.added.append(filepath)
        elif status.startswith("M") or status.startswith("R"):
            result.modified.append(filepath)
        elif status.startswith("D"):
            result.deleted.append(filepath)

    return result


def scan_files(
    repo: Path,
    *,
    include_patterns: list[str] | None = None,
) -> list[str]:
    """Return all tracked files in *repo*, optionally filtered by patterns."""
    try:
        output = _run_git(repo, "ls-files")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files = output.splitlines() if output else []
    if include_patterns:
        files = [f for f in files if _matches_any(f, include_patterns)]
    return sorted(files)


def _matches_any(filepath: str, patterns: list[str]) -> bool:
    """Return True if *filepath* matches any of the glob *patterns*.

    Handles ``**`` patterns manually since ``PurePath.match`` doesn't
    support recursive globs reliably across Python versions.
    """
    import fnmatch

    for pattern in patterns:
        # Simple pattern without ** — use fnmatch directly
        if "**" not in pattern:
            if fnmatch.fnmatch(filepath, pattern):
                return True
            continue

        # Pattern like "specs/**/*.md" or "**/*.md"
        # Split on **/ and check prefix + suffix
        parts = pattern.split("**/", 1)
        prefix = parts[0]  # e.g. "specs/" or ""
        suffix = parts[1] if len(parts) > 1 else ""  # e.g. "*.md"

        # Check prefix match
        if prefix and not filepath.startswith(prefix):
            continue

        # Check suffix match on the remainder
        remainder = filepath[len(prefix):]
        # The suffix may apply to any nested level, so check the filename
        # or any subpath. For "*.md" we check if the file itself matches.
        if fnmatch.fnmatch(remainder, suffix):
            return True
        # Also check just the filename for deeply nested paths
        filename = Path(filepath).name
        if fnmatch.fnmatch(filename, suffix):
            if not prefix or filepath.startswith(prefix):
                return True

    return False
