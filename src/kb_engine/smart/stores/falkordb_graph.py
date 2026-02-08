"""FalkorDB graph store for knowledge graph storage."""

from pathlib import Path
from typing import Any

import structlog
from redislite.falkordb_client import FalkorDB

logger = structlog.get_logger(__name__)


class FalkorDBGraphStore:
    """Graph store backed by FalkorDB (FalkorDBLite) embedded database.

    Provides storage for:
    - Entity nodes (domain entities)
    - Concept nodes (attributes, states)
    - Event nodes (domain events)
    - Relationships between nodes

    FalkorDB is schema-less and supports full MERGE...ON CREATE SET...ON MATCH SET syntax,
    making upserts much simpler than Kuzu.

    Usage:
        store = FalkorDBGraphStore("./kb-graph.db")
        store.initialize()

        # Add nodes
        store.upsert_entity("Usuario", {"code_class": "User"})
        store.upsert_concept("Usuario.email", "attribute", {"type": "string"})

        # Add relationships
        store.add_relationship("Usuario", "Usuario.email", "CONTAINS")

        # Query
        results = store.execute_cypher(
            "MATCH (e:Entity)-[:CONTAINS]->(c:Concept) RETURN e.name, c.name"
        )
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize FalkorDB graph store.

        Args:
            db_path: Path to the FalkorDB database file.
        """
        self.db_path = Path(db_path)
        self._db: FalkorDB | None = None
        self._graph: Any = None  # FalkorDB Graph object
        self._initialized = False

    def initialize(self, reset: bool = False) -> None:
        """Initialize the database.

        Args:
            reset: If True, delete existing database and start fresh.
        """
        log = logger.bind(db_path=str(self.db_path))

        if reset and self.db_path.exists():
            log.info("falkordb.reset", action="deleting existing database")
            self.db_path.unlink()

        log.debug("falkordb.initialize.start")

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize FalkorDB with file path
        self._db = FalkorDB(str(self.db_path))
        self._graph = self._db.select_graph("knowledge")

        if not self._initialized or reset:
            self._create_indexes()
            self._initialized = True

        log.info("falkordb.initialize.complete")

    def _create_indexes(self) -> None:
        """Create indexes for better query performance.

        FalkorDB is schema-less, so we only create indexes, not schema.
        """
        log = logger.bind(db_path=str(self.db_path))
        log.debug("falkordb.indexes.create")

        # Create indexes on id property for each node type
        try:
            self._graph.query("CREATE INDEX FOR (e:Entity) ON (e.id)")
        except Exception:
            pass  # Index may already exist

        try:
            self._graph.query("CREATE INDEX FOR (c:Concept) ON (c.id)")
        except Exception:
            pass

        try:
            self._graph.query("CREATE INDEX FOR (ev:Event) ON (ev.id)")
        except Exception:
            pass

        log.debug("falkordb.indexes.created")

    @property
    def graph(self) -> Any:
        """Get graph instance, initializing if needed."""
        if self._graph is None:
            self.initialize()
        return self._graph

    def close(self) -> None:
        """Close database connection."""
        # FalkorDBLite doesn't have an explicit close method
        # Just release the references
        self._graph = None
        self._db = None

    # === Node Operations ===

    def upsert_entity(
        self,
        entity_id: str,
        name: str,
        description: str = "",
        code_class: str | None = None,
        code_table: str | None = None,
        source_doc_id: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Insert or update an Entity node."""
        log = logger.bind(entity_id=entity_id, name=name)
        params = {
            "id": entity_id,
            "name": name,
            "descr": description[:500] if description else "",
            "code_class": code_class or "",
            "code_table": code_table or "",
            "source_doc": source_doc_id or "",
            "confidence": confidence,
        }

        try:
            self.graph.query(
                """
                MERGE (e:Entity {id: $id})
                ON CREATE SET e.name = $name, e.description = $descr, e.code_class = $code_class,
                    e.code_table = $code_table, e.source_doc_id = $source_doc, e.confidence = $confidence
                ON MATCH SET e.name = $name, e.description = $descr, e.code_class = $code_class,
                    e.code_table = $code_table, e.source_doc_id = $source_doc, e.confidence = $confidence
                """,
                params=params,
            )
            log.debug("falkordb.entity.upserted")
        except Exception as e:
            log.warning("falkordb.entity.upsert_failed", error=str(e))
            raise

    def upsert_concept(
        self,
        concept_id: str,
        name: str,
        concept_type: str,
        description: str = "",
        parent_entity: str | None = None,
        properties: dict[str, Any] | None = None,
        source_doc_id: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Insert or update a Concept node."""
        import json

        log = logger.bind(concept_id=concept_id, concept_type=concept_type)
        params = {
            "id": concept_id,
            "name": name,
            "ctype": concept_type,
            "descr": description[:500] if description else "",
            "parent": parent_entity or "",
            "props": json.dumps(properties) if properties else "{}",
            "source_doc": source_doc_id or "",
            "confidence": confidence,
        }

        try:
            self.graph.query(
                """
                MERGE (c:Concept {id: $id})
                ON CREATE SET c.name = $name, c.concept_type = $ctype, c.description = $descr,
                    c.parent_entity = $parent, c.properties = $props,
                    c.source_doc_id = $source_doc, c.confidence = $confidence
                ON MATCH SET c.name = $name, c.concept_type = $ctype, c.description = $descr,
                    c.parent_entity = $parent, c.properties = $props,
                    c.source_doc_id = $source_doc, c.confidence = $confidence
                """,
                params=params,
            )
            log.debug("falkordb.concept.upserted")
        except Exception as e:
            log.warning("falkordb.concept.upsert_failed", error=str(e))
            raise

    def upsert_event(
        self,
        event_id: str,
        name: str,
        description: str = "",
        source_doc_id: str | None = None,
    ) -> None:
        """Insert or update an Event node."""
        log = logger.bind(event_id=event_id, name=name)
        params = {
            "id": event_id,
            "name": name,
            "descr": description[:500] if description else "",
            "source_doc": source_doc_id or "",
        }

        try:
            self.graph.query(
                """
                MERGE (e:Event {id: $id})
                ON CREATE SET e.name = $name, e.description = $descr, e.source_doc_id = $source_doc
                ON MATCH SET e.name = $name, e.description = $descr, e.source_doc_id = $source_doc
                """,
                params=params,
            )
            log.debug("falkordb.event.upserted")
        except Exception as e:
            log.warning("falkordb.event.upsert_failed", error=str(e))
            raise

    # === Relationship Operations ===

    def add_contains(
        self,
        entity_id: str,
        concept_id: str,
        confidence: float = 1.0,
        source_doc_id: str | None = None,
    ) -> None:
        """Add CONTAINS relationship from Entity to Concept."""
        params = {
            "eid": entity_id,
            "cid": concept_id,
            "conf": confidence,
            "source": source_doc_id or "",
        }
        try:
            self.graph.query(
                """
                MATCH (e:Entity {id: $eid}), (c:Concept {id: $cid})
                MERGE (e)-[r:CONTAINS]->(c)
                ON CREATE SET r.confidence = $conf, r.source_doc_id = $source
                """,
                params=params,
            )
        except Exception as e:
            logger.warning(
                "falkordb.contains.failed", entity=entity_id, concept=concept_id, error=str(e)
            )

    def add_references(
        self,
        from_entity_id: str,
        to_entity_id: str,
        via_attribute: str | None = None,
        cardinality: str | None = None,
        description: str = "",
        confidence: float = 1.0,
        source_doc_id: str | None = None,
    ) -> None:
        """Add REFERENCES relationship between Entities."""
        params = {
            "eid1": from_entity_id,
            "eid2": to_entity_id,
            "via": via_attribute or "",
            "card": cardinality or "",
            "descr": description,
            "conf": confidence,
            "source": source_doc_id or "",
        }
        try:
            self.graph.query(
                """
                MATCH (e1:Entity {id: $eid1}), (e2:Entity {id: $eid2})
                MERGE (e1)-[r:REFERENCES]->(e2)
                ON CREATE SET r.via_attribute = $via, r.cardinality = $card,
                    r.description = $descr, r.confidence = $conf, r.source_doc_id = $source
                """,
                params=params,
            )
        except Exception as e:
            logger.warning(
                "falkordb.references.failed",
                from_id=from_entity_id,
                to_id=to_entity_id,
                error=str(e),
            )

    def add_produces(
        self,
        entity_id: str,
        event_id: str,
        confidence: float = 1.0,
        source_doc_id: str | None = None,
    ) -> None:
        """Add PRODUCES relationship from Entity to Event."""
        params = {
            "eid": entity_id,
            "evid": event_id,
            "conf": confidence,
            "source": source_doc_id or "",
        }
        try:
            self.graph.query(
                """
                MATCH (e:Entity {id: $eid}), (ev:Event {id: $evid})
                MERGE (e)-[r:PRODUCES]->(ev)
                ON CREATE SET r.confidence = $conf, r.source_doc_id = $source
                """,
                params=params,
            )
        except Exception as e:
            logger.warning(
                "falkordb.produces.failed", entity=entity_id, event=event_id, error=str(e)
            )

    def add_consumes(
        self,
        entity_id: str,
        event_id: str,
        confidence: float = 1.0,
        source_doc_id: str | None = None,
    ) -> None:
        """Add CONSUMES relationship from Entity to Event."""
        params = {
            "eid": entity_id,
            "evid": event_id,
            "conf": confidence,
            "source": source_doc_id or "",
        }
        try:
            self.graph.query(
                """
                MATCH (e:Entity {id: $eid}), (ev:Event {id: $evid})
                MERGE (e)-[r:CONSUMES]->(ev)
                ON CREATE SET r.confidence = $conf, r.source_doc_id = $source
                """,
                params=params,
            )
        except Exception as e:
            logger.warning(
                "falkordb.consumes.failed", entity=entity_id, event=event_id, error=str(e)
            )

    # === Query Operations ===

    def execute_cypher(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute a Cypher query and return results as list of dicts."""
        result = self.graph.query(query, params=params or {})
        if not result.result_set:
            return []
        # Extract column names from header
        headers = [col[1] if isinstance(col, (list, tuple)) else str(col) for col in result.header]
        return [dict(zip(headers, row)) for row in result.result_set]

    def get_entity(self, entity_id: str) -> dict | None:
        """Get an entity by ID."""
        results = self.execute_cypher(
            "MATCH (e:Entity {id: $id}) RETURN e", {"id": entity_id}
        )
        return results[0] if results else None

    def get_entity_graph(self, entity_id: str, depth: int = 2) -> dict:
        """Get an entity and all related nodes up to depth."""
        nodes = self.execute_cypher(
            f"""
            MATCH (e:Entity {{id: $id}})-[*1..{depth}]-(n)
            RETURN DISTINCT labels(n)[0] as node_type, n.id as id, n.name as name
            """,
            {"id": entity_id},
        )

        # Get relationship types using type() function (FalkorDB supports this)
        edges = self.execute_cypher(
            """
            MATCH (e:Entity {id: $id})-[r]-()
            RETURN DISTINCT type(r) as rel_type
            """,
            {"id": entity_id},
        )
        edge_types = [e["rel_type"] for e in edges]

        return {
            "center": entity_id,
            "nodes": nodes,
            "edge_types": edge_types,
        }

    def get_all_entities(self) -> list[dict]:
        """Get all entities."""
        return self.execute_cypher(
            "MATCH (e:Entity) RETURN e.id as id, e.name as name, e.code_class as code_class"
        )

    def find_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5,
    ) -> list[dict]:
        """Find path between two nodes."""
        return self.execute_cypher(
            f"""
            MATCH (a {{id: $from}})-[*1..{max_depth}]-(b {{id: $to}})
            RETURN a.name as start_name, b.name as end_name
            """,
            {"from": from_id, "to": to_id},
        )

    # === Utility ===

    def delete_by_source_doc(self, source_doc_id: str) -> None:
        """Delete all nodes and relationships from a source document."""
        log = logger.bind(source_doc_id=source_doc_id)
        log.debug("falkordb.delete_by_source.start")

        # Delete relationships first
        for rel_type in ["CONTAINS", "REFERENCES", "PRODUCES", "CONSUMES", "RELATED_TO"]:
            try:
                self.graph.query(
                    f"""
                    MATCH ()-[r:{rel_type}]->()
                    WHERE r.source_doc_id = $doc_id
                    DELETE r
                    """,
                    params={"doc_id": source_doc_id},
                )
            except Exception:
                pass

        # Delete nodes
        for node_type in ["Entity", "Concept", "Event"]:
            try:
                self.graph.query(
                    f"""
                    MATCH (n:{node_type})
                    WHERE n.source_doc_id = $doc_id
                    DELETE n
                    """,
                    params={"doc_id": source_doc_id},
                )
            except Exception:
                pass

        log.info("falkordb.delete_by_source.complete")

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}

        for node_type in ["Entity", "Concept", "Event"]:
            try:
                result = self.execute_cypher(f"MATCH (n:{node_type}) RETURN count(n) as cnt")
                stats[f"{node_type.lower()}_count"] = result[0]["cnt"] if result else 0
            except Exception:
                stats[f"{node_type.lower()}_count"] = 0

        return stats
