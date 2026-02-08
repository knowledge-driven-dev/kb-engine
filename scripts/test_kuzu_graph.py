#!/usr/bin/env python
"""Proof of concept: Kuzu as graph store for kb-engine.

Tests:
1. Schema creation for KDD entities
2. Node and edge insertion
3. Cypher queries (traversal, pattern matching)
4. AST-like deep traversal
"""

import shutil
from pathlib import Path

import kuzu

# Use temp directory for test
DB_PATH = Path("/tmp/kb-engine-kuzu-test")

def setup_database():
    """Create fresh database and schema."""
    # Clean up previous test
    if DB_PATH.exists():
        shutil.rmtree(DB_PATH)

    db = kuzu.Database(str(DB_PATH))
    conn = kuzu.Connection(db)

    # Create node tables
    print("Creating schema...")

    # Entity nodes (main domain entities)
    conn.execute("""
        CREATE NODE TABLE Entity(
            id STRING,
            name STRING,
            description STRING,
            code_class STRING,
            code_table STRING,
            PRIMARY KEY(id)
        )
    """)

    # Concept nodes (attributes, states, etc.)
    conn.execute("""
        CREATE NODE TABLE Concept(
            id STRING,
            name STRING,
            concept_type STRING,
            description STRING,
            parent_entity STRING,
            PRIMARY KEY(id)
        )
    """)

    # Event nodes
    conn.execute("""
        CREATE NODE TABLE Event(
            id STRING,
            name STRING,
            description STRING,
            PRIMARY KEY(id)
        )
    """)

    # For AST testing - Function nodes
    conn.execute("""
        CREATE NODE TABLE Function(
            id STRING,
            name STRING,
            file_path STRING,
            line_number INT64,
            PRIMARY KEY(id)
        )
    """)

    # Create relationship tables
    print("Creating relationships...")

    # Entity relationships
    conn.execute("CREATE REL TABLE CONTAINS(FROM Entity TO Concept, confidence FLOAT)")
    conn.execute("CREATE REL TABLE REFERENCES(FROM Entity TO Entity, via_attribute STRING)")
    conn.execute("CREATE REL TABLE PRODUCES(FROM Entity TO Event)")
    conn.execute("CREATE REL TABLE CONSUMES(FROM Entity TO Event)")

    # For AST - function calls
    conn.execute("CREATE REL TABLE CALLS(FROM Function TO Function, call_type STRING)")

    print("Schema created successfully!")
    return db, conn


def insert_usuario_data(conn):
    """Insert data from Usuario entity."""
    print("\nInserting Usuario entity data...")

    # Main entity
    conn.execute("""
        CREATE (e:Entity {
            id: 'entity:Usuario',
            name: 'Usuario',
            description: 'Representa a una persona que interactúa con el sistema',
            code_class: 'User',
            code_table: 'users'
        })
    """)

    # Related entities (referenced)
    for entity in ['Organizacion', 'RolUsuario', 'Documento', 'Proyecto']:
        conn.execute(f"""
            CREATE (e:Entity {{
                id: 'entity:{entity}',
                name: '{entity}',
                description: 'Entidad relacionada con Usuario',
                code_class: '{entity}',
                code_table: '{entity.lower()}s'
            }})
        """)

    # Attributes as Concepts
    attributes = [
        ('id', 'uuid', 'Identificador único'),
        ('email', 'string', 'Correo electrónico único'),
        ('nombre', 'string', 'Nombre de pila'),
        ('apellido', 'string', 'Apellido'),
        ('estado', 'enum', 'Estado del ciclo de vida'),
        ('organizacion_id', 'reference', 'Organización principal'),
    ]

    for attr_name, attr_type, desc in attributes:
        conn.execute(f"""
            CREATE (c:Concept {{
                id: 'concept:Usuario.{attr_name}',
                name: '{attr_name}',
                concept_type: 'attribute',
                description: '{desc}',
                parent_entity: 'Usuario'
            }})
        """)

    # States as Concepts
    states = ['Pendiente', 'Activo', 'Suspendido', 'Inactivo', 'Eliminado']
    for state in states:
        conn.execute(f"""
            CREATE (c:Concept {{
                id: 'concept:Usuario::{state}',
                name: '{state}',
                concept_type: 'state',
                description: 'Estado del ciclo de vida',
                parent_entity: 'Usuario'
            }})
        """)

    # Events
    events = [
        'EVT-Usuario-Registrado',
        'EVT-Usuario-Verificado',
        'EVT-Usuario-Actualizado',
        'EVT-Usuario-Suspendido',
        'EVT-Usuario-Eliminado',
        'EVT-Organizacion-Eliminada',
    ]
    for event in events:
        conn.execute(f"""
            CREATE (e:Event {{
                id: 'event:{event}',
                name: '{event}',
                description: 'Evento de dominio'
            }})
        """)

    print(f"  Created 1 main entity + 4 related entities")
    print(f"  Created {len(attributes)} attributes + {len(states)} states")
    print(f"  Created {len(events)} events")

    # Create relationships
    print("\nCreating relationships...")

    # Entity CONTAINS attributes
    for attr_name, _, _ in attributes:
        conn.execute(f"""
            MATCH (e:Entity {{id: 'entity:Usuario'}}), (c:Concept {{id: 'concept:Usuario.{attr_name}'}})
            CREATE (e)-[:CONTAINS {{confidence: 1.0}}]->(c)
        """)

    # Entity CONTAINS states
    for state in states:
        conn.execute(f"""
            MATCH (e:Entity {{id: 'entity:Usuario'}}), (c:Concept {{id: 'concept:Usuario::{state}'}})
            CREATE (e)-[:CONTAINS {{confidence: 1.0}}]->(c)
        """)

    # Entity REFERENCES other entities
    references = [
        ('Organizacion', 'organizacion_id'),
        ('RolUsuario', 'roles'),
        ('Documento', 'documents'),
        ('Proyecto', 'projects'),
    ]
    for target, via in references:
        conn.execute(f"""
            MATCH (e1:Entity {{id: 'entity:Usuario'}}), (e2:Entity {{id: 'entity:{target}'}})
            CREATE (e1)-[:REFERENCES {{via_attribute: '{via}'}}]->(e2)
        """)

    # Entity PRODUCES events
    produced_events = [
        'EVT-Usuario-Registrado',
        'EVT-Usuario-Verificado',
        'EVT-Usuario-Actualizado',
        'EVT-Usuario-Suspendido',
        'EVT-Usuario-Eliminado',
    ]
    for event in produced_events:
        conn.execute(f"""
            MATCH (e:Entity {{id: 'entity:Usuario'}}), (ev:Event {{id: 'event:{event}'}})
            CREATE (e)-[:PRODUCES]->(ev)
        """)

    # Entity CONSUMES events
    conn.execute("""
        MATCH (e:Entity {id: 'entity:Usuario'}), (ev:Event {id: 'event:EVT-Organizacion-Eliminada'})
        CREATE (e)-[:CONSUMES]->(ev)
    """)

    print("  Relationships created!")


def insert_ast_data(conn):
    """Insert mock AST data to test deep traversal."""
    print("\nInserting mock AST data...")

    # Create a call chain: main -> auth -> validate -> hash -> encode
    functions = [
        ('main', 'app.py', 10),
        ('authenticate', 'auth/service.py', 25),
        ('validate_credentials', 'auth/validator.py', 15),
        ('hash_password', 'crypto/hash.py', 8),
        ('encode_base64', 'crypto/encoding.py', 5),
        ('log_attempt', 'logging/audit.py', 20),
        ('send_notification', 'notifications/email.py', 30),
    ]

    for name, path, line in functions:
        conn.execute(f"""
            CREATE (f:Function {{
                id: 'func:{name}',
                name: '{name}',
                file_path: '{path}',
                line_number: {line}
            }})
        """)

    # Create call relationships (a tree structure)
    calls = [
        ('main', 'authenticate', 'direct'),
        ('main', 'log_attempt', 'direct'),
        ('authenticate', 'validate_credentials', 'direct'),
        ('authenticate', 'send_notification', 'async'),
        ('validate_credentials', 'hash_password', 'direct'),
        ('hash_password', 'encode_base64', 'direct'),
    ]

    for caller, callee, call_type in calls:
        conn.execute(f"""
            MATCH (f1:Function {{id: 'func:{caller}'}}), (f2:Function {{id: 'func:{callee}'}})
            CREATE (f1)-[:CALLS {{call_type: '{call_type}'}}]->(f2)
        """)

    print(f"  Created {len(functions)} functions with {len(calls)} call relationships")


def test_queries(conn):
    """Test various Cypher queries."""
    print("\n" + "="*60)
    print("TESTING CYPHER QUERIES")
    print("="*60)

    # Query 1: Simple node lookup
    print("\n1. Find Usuario entity:")
    result = conn.execute("""
        MATCH (e:Entity {name: 'Usuario'})
        RETURN e.name, e.code_class, e.code_table
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 2: Get all attributes of Usuario
    print("\n2. Get Usuario attributes:")
    result = conn.execute("""
        MATCH (e:Entity {name: 'Usuario'})-[:CONTAINS]->(c:Concept {concept_type: 'attribute'})
        RETURN c.name as attribute, c.description
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 3: Get all entities referenced by Usuario
    print("\n3. Entities referenced by Usuario:")
    result = conn.execute("""
        MATCH (e:Entity {name: 'Usuario'})-[r:REFERENCES]->(target:Entity)
        RETURN target.name as entity, r.via_attribute as via
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 4: Get events produced by Usuario
    print("\n4. Events produced by Usuario:")
    result = conn.execute("""
        MATCH (e:Entity {name: 'Usuario'})-[:PRODUCES]->(ev:Event)
        RETURN ev.name as event
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 5: Pattern matching - entities that produce AND consume events
    print("\n5. Entities that both produce and consume events:")
    result = conn.execute("""
        MATCH (e:Entity)-[:PRODUCES]->(ev1:Event)
        MATCH (e)-[:CONSUMES]->(ev2:Event)
        RETURN DISTINCT e.name as entity, count(DISTINCT ev1) as produces, count(DISTINCT ev2) as consumes
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 6: Variable-length path - all concepts within 2 hops
    print("\n6. All nodes within 2 hops of Usuario:")
    result = conn.execute("""
        MATCH (e:Entity {name: 'Usuario'})-[*1..2]->(n)
        RETURN DISTINCT labels(n)[0] as type, n.name as name
        LIMIT 15
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 7: AST deep traversal - all functions called from main
    print("\n7. AST: All functions called from main (any depth):")
    result = conn.execute("""
        MATCH (main:Function {name: 'main'})-[:CALLS*1..10]->(f:Function)
        RETURN f.name as function, f.file_path as file
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))

    # Query 8: AST path - show call chain to encode_base64
    print("\n8. AST: Call chain from main to encode_base64:")
    result = conn.execute("""
        MATCH (f1:Function {name: 'main'})-[:CALLS*]->(f2:Function {name: 'encode_base64'})
        RETURN f1.name as caller, f2.name as callee
    """)
    df = result.get_as_df()
    print(df.to_string(index=False))


def test_performance(conn):
    """Quick performance test."""
    print("\n" + "="*60)
    print("PERFORMANCE TEST")
    print("="*60)

    import time

    # Time a complex query
    start = time.perf_counter()
    for _ in range(100):
        conn.execute("""
            MATCH (e:Entity {name: 'Usuario'})-[:CONTAINS]->(c:Concept)
            RETURN c.name, c.concept_type
        """)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"\n100x attribute lookup: {elapsed:.2f}ms ({elapsed/100:.3f}ms per query)")

    # Time traversal query
    start = time.perf_counter()
    for _ in range(100):
        conn.execute("""
            MATCH (main:Function {name: 'main'})-[:CALLS*1..5]->(f:Function)
            RETURN f.name
        """)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"100x AST traversal (depth 5): {elapsed:.2f}ms ({elapsed/100:.3f}ms per query)")


def main():
    print("="*60)
    print("KUZU GRAPH DATABASE - PROOF OF CONCEPT")
    print("="*60)
    print(f"\nDatabase path: {DB_PATH}")

    db, conn = setup_database()
    insert_usuario_data(conn)
    insert_ast_data(conn)
    test_queries(conn)
    test_performance(conn)

    # Show database size
    import os
    total_size = sum(
        f.stat().st_size for f in DB_PATH.rglob('*') if f.is_file()
    )
    print(f"\n" + "="*60)
    print(f"Database size: {total_size / 1024:.1f} KB")
    print(f"Location: {DB_PATH}")
    print("="*60)


if __name__ == "__main__":
    main()
