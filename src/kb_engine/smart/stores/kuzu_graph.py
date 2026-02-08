"""Kuzu graph store for knowledge graph storage."""

import shutil
from pathlib import Path
from typing import Any

import kuzu
import structlog

logger = structlog.get_logger(__name__)


class KuzuGraphStore:
    """Graph store backed by Kuzu embedded database.

    Provides storage for:
    - Entity nodes (domain entities)
    - Concept nodes (attributes, states)
    - Event nodes (domain events)
    - Relationships between nodes

    Usage:
        store = KuzuGraphStore("./kb-graph")
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
        """Initialize Kuzu graph store.

        Args:
            db_path: Path to the Kuzu database directory.
        """
        self.db_path = Path(db_path)
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None
        self._initialized = False

    def initialize(self, reset: bool = False) -> None:
        """Initialize the database and create schema.

        Args:
            reset: If True, delete existing database and start fresh.
        """
        log = logger.bind(db_path=str(self.db_path))

        if reset and self.db_path.exists():
            log.info("kuzu.reset", action="deleting existing database")
            shutil.rmtree(self.db_path)

        log.debug("kuzu.initialize.start")
        self._db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(self._db)

        if not self._initialized or reset:
            self._create_schema()
            self._initialized = True

        log.info("kuzu.initialize.complete")

    def _create_schema(self) -> None:
        """Create the graph schema if it doesn't exist."""
        log = logger.bind(db_path=str(self.db_path))

        # Check if schema exists by trying to query
        try:
            self._conn.execute("MATCH (e:Entity) RETURN e LIMIT 1")
            log.debug("kuzu.schema.exists")
            return
        except RuntimeError:
            pass  # Schema doesn't exist, create it

        log.debug("kuzu.schema.create")

        # Node tables
        self._conn.execute("""
            CREATE NODE TABLE Entity(
                id STRING,
                name STRING,
                description STRING,
                code_class STRING,
                code_table STRING,
                source_doc_id STRING,
                confidence DOUBLE,
                PRIMARY KEY(id)
            )
        """)

        self._conn.execute("""
            CREATE NODE TABLE Concept(
                id STRING,
                name STRING,
                concept_type STRING,
                description STRING,
                parent_entity STRING,
                properties STRING,
                source_doc_id STRING,
                confidence DOUBLE,
                PRIMARY KEY(id)
            )
        """)

        self._conn.execute("""
            CREATE NODE TABLE Event(
                id STRING,
                name STRING,
                description STRING,
                source_doc_id STRING,
                PRIMARY KEY(id)
            )
        """)

        # Relationship tables
        self._conn.execute("""
            CREATE REL TABLE CONTAINS(
                FROM Entity TO Concept,
                confidence DOUBLE,
                source_doc_id STRING
            )
        """)

        self._conn.execute("""
            CREATE REL TABLE REFERENCES(
                FROM Entity TO Entity,
                via_attribute STRING,
                cardinality STRING,
                description STRING,
                confidence DOUBLE,
                source_doc_id STRING
            )
        """)

        self._conn.execute("""
            CREATE REL TABLE PRODUCES(
                FROM Entity TO Event,
                confidence DOUBLE,
                source_doc_id STRING
            )
        """)

        self._conn.execute("""
            CREATE REL TABLE CONSUMES(
                FROM Entity TO Event,
                confidence DOUBLE,
                source_doc_id STRING
            )
        """)

        self._conn.execute("""
            CREATE REL TABLE RELATED_TO(
                FROM Entity TO Entity,
                relation_type STRING,
                description STRING,
                confidence DOUBLE,
                source_doc_id STRING
            )
        """)

        log.info("kuzu.schema.created")

    @property
    def connection(self) -> kuzu.Connection:
        """Get database connection, initializing if needed."""
        if self._conn is None:
            self.initialize()
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        self._conn = None
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
            # Check if entity exists
            result = self.connection.execute(
                "MATCH (e:Entity {id: $id}) RETURN e.id",
                {"id": entity_id}
            )
            exists = len(result.get_as_df()) > 0

            if exists:
                # Update existing
                self.connection.execute("""
                    MATCH (e:Entity {id: $id})
                    SET e.name = $name, e.description = $descr, e.code_class = $code_class,
                        e.code_table = $code_table, e.source_doc_id = $source_doc, e.confidence = $confidence
                """, params)
            else:
                # Create new - Kuzu requires CREATE then SET for parameters
                self.connection.execute("CREATE (e:Entity {id: $id})", {"id": entity_id})
                self.connection.execute("""
                    MATCH (e:Entity {id: $id})
                    SET e.name = $name, e.description = $descr, e.code_class = $code_class,
                        e.code_table = $code_table, e.source_doc_id = $source_doc, e.confidence = $confidence
                """, params)
            log.debug("kuzu.entity.upserted")
        except RuntimeError as e:
            log.warning("kuzu.entity.upsert_failed", error=str(e))
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
            # Check if concept exists
            result = self.connection.execute(
                "MATCH (c:Concept {id: $id}) RETURN c.id",
                {"id": concept_id}
            )
            exists = len(result.get_as_df()) > 0

            if exists:
                # Update existing
                self.connection.execute("""
                    MATCH (c:Concept {id: $id})
                    SET c.name = $name, c.concept_type = $ctype, c.description = $descr,
                        c.parent_entity = $parent, c.properties = $props,
                        c.source_doc_id = $source_doc, c.confidence = $confidence
                """, params)
            else:
                # Create new - Kuzu requires CREATE then SET for parameters
                self.connection.execute("CREATE (c:Concept {id: $id})", {"id": concept_id})
                self.connection.execute("""
                    MATCH (c:Concept {id: $id})
                    SET c.name = $name, c.concept_type = $ctype, c.description = $descr,
                        c.parent_entity = $parent, c.properties = $props,
                        c.source_doc_id = $source_doc, c.confidence = $confidence
                """, params)
            log.debug("kuzu.concept.upserted")
        except RuntimeError as e:
            log.warning("kuzu.concept.upsert_failed", error=str(e))
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
            # Check if event exists
            result = self.connection.execute(
                "MATCH (e:Event {id: $id}) RETURN e.id",
                {"id": event_id}
            )
            exists = len(result.get_as_df()) > 0

            if exists:
                # Update existing
                self.connection.execute("""
                    MATCH (e:Event {id: $id})
                    SET e.name = $name, e.description = $descr, e.source_doc_id = $source_doc
                """, params)
            else:
                # Create new - Kuzu requires CREATE then SET for parameters
                self.connection.execute("CREATE (e:Event {id: $id})", {"id": event_id})
                self.connection.execute("""
                    MATCH (e:Event {id: $id})
                    SET e.name = $name, e.description = $descr, e.source_doc_id = $source_doc
                """, params)
            log.debug("kuzu.event.upserted")
        except RuntimeError as e:
            log.warning("kuzu.event.upsert_failed", error=str(e))
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
            # Check if relationship exists
            result = self.connection.execute("""
                MATCH (e:Entity {id: $eid})-[r:CONTAINS]->(c:Concept {id: $cid})
                RETURN r
            """, {"eid": entity_id, "cid": concept_id})
            exists = len(result.get_as_df()) > 0

            if not exists:
                # Create relationship
                self.connection.execute("""
                    MATCH (e:Entity {id: $eid}), (c:Concept {id: $cid})
                    CREATE (e)-[:CONTAINS {confidence: $conf, source_doc_id: $source}]->(c)
                """, params)
        except RuntimeError as e:
            logger.warning("kuzu.contains.failed", entity=entity_id, concept=concept_id, error=str(e))

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
            # Check if relationship exists
            result = self.connection.execute("""
                MATCH (e1:Entity {id: $eid1})-[r:REFERENCES]->(e2:Entity {id: $eid2})
                RETURN r
            """, {"eid1": from_entity_id, "eid2": to_entity_id})
            exists = len(result.get_as_df()) > 0

            if not exists:
                # Create relationship
                self.connection.execute("""
                    MATCH (e1:Entity {id: $eid1}), (e2:Entity {id: $eid2})
                    CREATE (e1)-[:REFERENCES {
                        via_attribute: $via, cardinality: $card, description: $descr,
                        confidence: $conf, source_doc_id: $source
                    }]->(e2)
                """, params)
        except RuntimeError as e:
            logger.warning("kuzu.references.failed", from_id=from_entity_id, to_id=to_entity_id, error=str(e))

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
            # Check if relationship exists
            result = self.connection.execute("""
                MATCH (e:Entity {id: $eid})-[r:PRODUCES]->(ev:Event {id: $evid})
                RETURN r
            """, {"eid": entity_id, "evid": event_id})
            exists = len(result.get_as_df()) > 0

            if not exists:
                # Create relationship
                self.connection.execute("""
                    MATCH (e:Entity {id: $eid}), (ev:Event {id: $evid})
                    CREATE (e)-[:PRODUCES {confidence: $conf, source_doc_id: $source}]->(ev)
                """, params)
        except RuntimeError as e:
            logger.warning("kuzu.produces.failed", entity=entity_id, event=event_id, error=str(e))

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
            # Check if relationship exists
            result = self.connection.execute("""
                MATCH (e:Entity {id: $eid})-[r:CONSUMES]->(ev:Event {id: $evid})
                RETURN r
            """, {"eid": entity_id, "evid": event_id})
            exists = len(result.get_as_df()) > 0

            if not exists:
                # Create relationship
                self.connection.execute("""
                    MATCH (e:Entity {id: $eid}), (ev:Event {id: $evid})
                    CREATE (e)-[:CONSUMES {confidence: $conf, source_doc_id: $source}]->(ev)
                """, params)
        except RuntimeError as e:
            logger.warning("kuzu.consumes.failed", entity=entity_id, event=event_id, error=str(e))

    # === Query Operations ===

    def execute_cypher(self, query: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Execute a Cypher query and return results as list of dicts."""
        result = self.connection.execute(query, params or {})
        df = result.get_as_df()
        return df.to_dict(orient="records")

    def get_entity(self, entity_id: str) -> dict | None:
        """Get an entity by ID."""
        results = self.execute_cypher(
            "MATCH (e:Entity {id: $id}) RETURN e",
            {"id": entity_id}
        )
        return results[0] if results else None

    def get_entity_graph(self, entity_id: str, depth: int = 2) -> dict:
        """Get an entity and all related nodes up to depth."""
        nodes = self.execute_cypher(f"""
            MATCH (e:Entity {{id: $id}})-[*1..{depth}]-(n)
            RETURN DISTINCT label(n) as node_type, n.id as id, n.name as name
        """, {"id": entity_id})

        # Query each relationship type separately since Kuzu doesn't have type() function
        edge_types = []
        for rel_type in ["CONTAINS", "REFERENCES", "PRODUCES", "CONSUMES", "RELATED_TO"]:
            try:
                result = self.execute_cypher(f"""
                    MATCH (e:Entity {{id: $id}})-[r:{rel_type}]-()
                    RETURN count(r) as cnt
                """, {"id": entity_id})
                if result and result[0]["cnt"] > 0:
                    edge_types.append(rel_type)
            except RuntimeError:
                pass

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
        return self.execute_cypher(f"""
            MATCH (a {{id: $from}})-[*1..{max_depth}]-(b {{id: $to}})
            RETURN a.name as start_name, b.name as end_name
        """, {"from": from_id, "to": to_id})

    # === Utility ===

    def delete_by_source_doc(self, source_doc_id: str) -> None:
        """Delete all nodes and relationships from a source document."""
        log = logger.bind(source_doc_id=source_doc_id)
        log.debug("kuzu.delete_by_source.start")

        # Delete relationships first (Kuzu requires this)
        for rel_type in ["CONTAINS", "REFERENCES", "PRODUCES", "CONSUMES", "RELATED_TO"]:
            try:
                self.connection.execute(f"""
                    MATCH ()-[r:{rel_type}]->()
                    WHERE r.source_doc_id = $doc_id
                    DELETE r
                """, {"doc_id": source_doc_id})
            except RuntimeError:
                pass

        # Delete nodes
        for node_type in ["Entity", "Concept", "Event"]:
            try:
                self.connection.execute(f"""
                    MATCH (n:{node_type})
                    WHERE n.source_doc_id = $doc_id
                    DELETE n
                """, {"doc_id": source_doc_id})
            except RuntimeError:
                pass

        log.info("kuzu.delete_by_source.complete")

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}

        for node_type in ["Entity", "Concept", "Event"]:
            try:
                result = self.execute_cypher(f"MATCH (n:{node_type}) RETURN count(n) as cnt")
                stats[f"{node_type.lower()}_count"] = result[0]["cnt"] if result else 0
            except RuntimeError:
                stats[f"{node_type.lower()}_count"] = 0

        return stats
