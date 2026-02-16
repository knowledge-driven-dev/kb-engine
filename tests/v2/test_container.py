"""Tests for the DI container (container.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from kdd.container import Container, create_container
from kdd.domain.enums import IndexLevel


class TestContainerCreation:
    def test_creates_l1_container_without_deps(self, tmp_path):
        """When sentence-transformers is not installed, container is L1."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            container = create_container(specs)

        assert isinstance(container, Container)
        assert container.index_level == IndexLevel.L1
        assert container.embedding_model is None
        assert container.vector_store is None
        assert container.specs_root == specs

    def test_default_index_path(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            container = create_container(specs)

        # Default: parent of specs_root / .kdd-index
        assert container.index_path == tmp_path / ".kdd-index"

    def test_custom_index_path(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()
        custom = tmp_path / "custom-idx"

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            container = create_container(specs, custom)

        assert container.index_path == custom

    def test_ensure_loaded_returns_false_without_index(self, tmp_path):
        specs = tmp_path / "specs"
        specs.mkdir()

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            container = create_container(specs)

        assert container.ensure_loaded() is False
