"""Tests for CLI graph commands."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kb_engine.cli import cli


@patch("kb_engine.cli._get_graph_store")
class TestGraphStats:
    def test_stats_human(self, mock_get_store):
        store = MagicMock()
        store.get_stats.return_value = {
            "entity_count": 10,
            "concept_count": 5,
            "event_count": 3,
            "document_count": 8,
        }
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "stats"])
        assert result.exit_code == 0
        assert "Entities:  10" in result.output
        assert "Concepts:  5" in result.output
        assert "Events:    3" in result.output
        assert "Documents: 8" in result.output
        assert "Total domain nodes: 18" in result.output

    def test_stats_json(self, mock_get_store):
        store = MagicMock()
        store.get_stats.return_value = {
            "entity_count": 10,
            "concept_count": 5,
            "event_count": 3,
            "document_count": 8,
        }
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "stats", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["entity_count"] == 10


@patch("kb_engine.cli._get_graph_store")
class TestGraphLs:
    def test_ls_all(self, mock_get_store):
        store = MagicMock()
        store.get_all_nodes.return_value = [
            {"label": "Entity", "id": "entity:User", "name": "User"},
            {"label": "Concept", "id": "concept:email", "name": "Email"},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "ls"])
        assert result.exit_code == 0
        assert "Found 2 nodes" in result.output
        assert "[Entity] entity:User" in result.output
        assert "[Concept] concept:email" in result.output
        store.get_all_nodes.assert_called_once_with(None)

    def test_ls_filtered(self, mock_get_store):
        store = MagicMock()
        store.get_all_nodes.return_value = [
            {"label": "Entity", "id": "entity:User", "name": "User"},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "ls", "--type", "entity"])
        assert result.exit_code == 0
        store.get_all_nodes.assert_called_once_with("entity")

    def test_ls_empty(self, mock_get_store):
        store = MagicMock()
        store.get_all_nodes.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "ls"])
        assert result.exit_code == 0
        assert "No nodes found" in result.output

    def test_ls_json(self, mock_get_store):
        store = MagicMock()
        store.get_all_nodes.return_value = [
            {"label": "Entity", "id": "entity:User", "name": "User"},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "ls", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["nodes"][0]["id"] == "entity:User"


@patch("kb_engine.cli._get_graph_store")
class TestGraphInspect:
    def test_inspect_human(self, mock_get_store):
        store = MagicMock()
        store.get_node_graph.return_value = {
            "center": "entity:User",
            "nodes": [{"node_type": "Concept", "id": "concept:email", "name": "Email"}],
            "edge_types": ["CONTAINS"],
        }
        store.get_node_provenance.return_value = [
            {"doc_id": "doc-1", "title": "User Entity", "path": "entities/User.md", "role": "primary", "confidence": 1.0},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "inspect", "entity:User"])
        assert result.exit_code == 0
        assert "Node: entity:User" in result.output
        assert "[Concept] concept:email" in result.output
        assert "CONTAINS" in result.output
        assert "[primary] doc-1" in result.output

    def test_inspect_json(self, mock_get_store):
        store = MagicMock()
        store.get_node_graph.return_value = {
            "center": "entity:User",
            "nodes": [],
            "edge_types": [],
        }
        store.get_node_provenance.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "inspect", "entity:User", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["neighborhood"]["center"] == "entity:User"
        assert data["provenance"] == []

    def test_inspect_custom_depth(self, mock_get_store):
        store = MagicMock()
        store.get_node_graph.return_value = {"center": "entity:User", "nodes": [], "edge_types": []}
        store.get_node_provenance.return_value = []
        mock_get_store.return_value = store

        CliRunner().invoke(cli, ["graph", "inspect", "entity:User", "-d", "3"])
        store.get_node_graph.assert_called_once_with("entity:User", depth=3)


@patch("kb_engine.cli._get_graph_store")
class TestGraphPath:
    def test_path_found(self, mock_get_store):
        store = MagicMock()
        store.find_path.return_value = [{"start_name": "User", "end_name": "Order"}]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "path", "entity:User", "entity:Order"])
        assert result.exit_code == 0
        assert "Path found: User -> Order" in result.output

    def test_path_not_found(self, mock_get_store):
        store = MagicMock()
        store.find_path.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "path", "entity:User", "entity:Order"])
        assert result.exit_code == 0
        assert "No path found" in result.output

    def test_path_json(self, mock_get_store):
        store = MagicMock()
        store.find_path.return_value = [{"start_name": "User", "end_name": "Order"}]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "path", "entity:User", "entity:Order", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["reachable"] is True
        assert data["from"] == "entity:User"

    def test_path_custom_depth(self, mock_get_store):
        store = MagicMock()
        store.find_path.return_value = []
        mock_get_store.return_value = store

        CliRunner().invoke(cli, ["graph", "path", "entity:User", "entity:Order", "--max-depth", "3"])
        store.find_path.assert_called_once_with("entity:User", "entity:Order", max_depth=3)


@patch("kb_engine.cli._get_graph_store")
class TestGraphImpact:
    def test_impact_human(self, mock_get_store):
        store = MagicMock()
        store.get_document_impact.return_value = [
            {"node_type": "Entity", "id": "entity:User", "name": "User", "role": "primary", "confidence": 1.0},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "impact", "doc-1"])
        assert result.exit_code == 0
        assert "1 nodes" in result.output
        assert "[Entity] entity:User" in result.output

    def test_impact_empty(self, mock_get_store):
        store = MagicMock()
        store.get_document_impact.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "impact", "doc-1"])
        assert result.exit_code == 0
        assert "No nodes found" in result.output

    def test_impact_json(self, mock_get_store):
        store = MagicMock()
        store.get_document_impact.return_value = [
            {"node_type": "Entity", "id": "entity:User", "name": "User", "role": "primary", "confidence": 1.0},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "impact", "doc-1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["doc_id"] == "doc-1"
        assert data["count"] == 1


@patch("kb_engine.cli._get_graph_store")
class TestGraphProvenance:
    def test_provenance_human(self, mock_get_store):
        store = MagicMock()
        store.get_node_provenance.return_value = [
            {"doc_id": "doc-1", "title": "User Entity", "path": "entities/User.md", "role": "primary", "confidence": 1.0},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "provenance", "entity:User"])
        assert result.exit_code == 0
        assert "1 documents" in result.output
        assert "[primary] doc-1" in result.output
        assert "entities/User.md" in result.output

    def test_provenance_empty(self, mock_get_store):
        store = MagicMock()
        store.get_node_provenance.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "provenance", "entity:User"])
        assert result.exit_code == 0
        assert "No provenance records" in result.output

    def test_provenance_json(self, mock_get_store):
        store = MagicMock()
        store.get_node_provenance.return_value = [
            {"doc_id": "doc-1", "title": "User Entity", "path": "entities/User.md", "role": "primary", "confidence": 1.0},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "provenance", "entity:User", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["node_id"] == "entity:User"
        assert data["count"] == 1


@patch("kb_engine.cli._get_graph_store")
class TestGraphCypher:
    def test_cypher_results(self, mock_get_store):
        store = MagicMock()
        store.execute_cypher.return_value = [
            {"type": "Entity", "cnt": 10},
            {"type": "Concept", "cnt": 5},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "cypher", "MATCH (n) RETURN labels(n)[0] as type, count(n) as cnt"])
        assert result.exit_code == 0
        assert "type" in result.output
        assert "Entity" in result.output

    def test_cypher_empty(self, mock_get_store):
        store = MagicMock()
        store.execute_cypher.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "cypher", "MATCH (n:Foo) RETURN n"])
        assert result.exit_code == 0
        assert "no results" in result.output

    def test_cypher_json(self, mock_get_store):
        store = MagicMock()
        store.execute_cypher.return_value = [{"type": "Entity", "cnt": 10}]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "cypher", "MATCH (n) RETURN n", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1

    def test_cypher_error(self, mock_get_store):
        store = MagicMock()
        store.execute_cypher.side_effect = Exception("Invalid syntax")
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "cypher", "INVALID QUERY"])
        assert result.exit_code != 0

    def test_cypher_error_json(self, mock_get_store):
        store = MagicMock()
        store.execute_cypher.side_effect = Exception("Invalid syntax")
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "cypher", "INVALID QUERY", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert "error" in data


@patch("kb_engine.cli._get_graph_store")
class TestGraphDelete:
    def test_delete_with_force(self, mock_get_store):
        store = MagicMock()
        store.delete_node.return_value = True
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "delete", "entity:User", "-f"])
        assert result.exit_code == 0
        assert "Deleted node: entity:User" in result.output
        store.delete_node.assert_called_once_with("entity:User")

    def test_delete_not_found(self, mock_get_store):
        store = MagicMock()
        store.delete_node.return_value = False
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "delete", "entity:Ghost", "-f"])
        assert result.exit_code == 0
        assert "Node not found: entity:Ghost" in result.output

    def test_delete_confirmation_yes(self, mock_get_store):
        store = MagicMock()
        store.delete_node.return_value = True
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "delete", "entity:User"], input="y\n")
        assert result.exit_code == 0
        assert "Deleted node: entity:User" in result.output

    def test_delete_confirmation_no(self, mock_get_store):
        store = MagicMock()
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "delete", "entity:User"], input="n\n")
        assert result.exit_code != 0  # click.confirm abort
        store.delete_node.assert_not_called()

    def test_delete_json(self, mock_get_store):
        store = MagicMock()
        store.delete_node.return_value = True
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "delete", "entity:User", "-f", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["deleted"] is True
        assert data["node_id"] == "entity:User"


@patch("kb_engine.cli._get_graph_store")
class TestGraphOrphans:
    def test_orphans_human(self, mock_get_store):
        store = MagicMock()
        store.get_orphan_entities.return_value = [
            {"name": "Order", "confidence": 0.7, "referenced_by": ["User Entity"]},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "orphans"])
        assert result.exit_code == 0
        assert "1 orphan" in result.output
        assert "Order" in result.output

    def test_orphans_json(self, mock_get_store):
        store = MagicMock()
        store.get_orphan_entities.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "orphans", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 0


@patch("kb_engine.cli._get_graph_store")
class TestGraphCompleteness:
    def test_completeness_human(self, mock_get_store):
        store = MagicMock()
        store.get_entity_completeness.return_value = [
            {"id": "entity:User", "name": "User", "confidence": 1.0, "status": "complete", "primary_docs": ["User Entity"], "referenced_by": []},
        ]
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "completeness"])
        assert result.exit_code == 0
        assert "1 total" in result.output
        assert "[OK] User" in result.output

    def test_completeness_json(self, mock_get_store):
        store = MagicMock()
        store.get_entity_completeness.return_value = []
        mock_get_store.return_value = store

        result = CliRunner().invoke(cli, ["graph", "completeness", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 0
