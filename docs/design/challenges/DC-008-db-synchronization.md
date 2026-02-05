# DC-008: Sincronización de BBDDs

---
id: DC-008
status: open
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El sistema utiliza 3 bases de datos que deben mantenerse sincronizadas:
- **PostgreSQL**: Trazabilidad (documentos, chunks, referencias)
- **Vector DB**: Embeddings para búsqueda semántica
- **Graph DB**: Nodos y relaciones del conocimiento

Las operaciones de indexación y eliminación deben mantener consistencia entre las tres.

### Requisitos ya definidos

- **Trazabilidad total**: Cada embedding y nodo tiene referencia a su origen
- **Actualización incremental**: Cambios en documentos deben propagarse correctamente
- **Eliminación en cascada**: Borrar documento elimina chunks, embeddings y nodos derivados

### Contexto Técnico

- PostgreSQL: Fuente de verdad para trazabilidad
- Vector DB: Qdrant/Weaviate/pgvector (operaciones específicas)
- Graph DB: Neo4j/NebulaGraph (operaciones específicas)
- Cada DB tiene su propia transaccionalidad

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Crear documento → insertar en las 3 BBDDs de forma consistente
- [ ] RF2: Actualizar documento → propagar cambios a las 3 BBDDs
- [ ] RF3: Eliminar documento → borrado en cascada en las 3 BBDDs
- [ ] RF4: Detectar y recuperar de inconsistencias
- [ ] RF5: Operaciones de reconciliación/reparación

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Consistencia eventual aceptable (no se requiere strict consistency)
- [ ] RNF2: Recuperación ante fallos parciales
- [ ] RNF3: Idempotencia en operaciones

### 2.3 Restricciones

- No hay transacciones distribuidas nativas entre las 3 BBDDs
- Cada BBDD puede fallar independientemente
- Debe funcionar con cualquier combinación de Vector + Graph DB

## 3. Opciones Consideradas

### Opción A: Orquestación Secuencial con Rollback Manual

**Descripción**: Ejecutar operaciones en secuencia, guardando estado para rollback si falla.

```python
async def create_document(doc):
    # 1. PostgreSQL primero (source of truth)
    pg_record = await pg.insert_document(doc)

    try:
        # 2. Vector DB
        vector_ids = await vector_db.insert_embeddings(doc.embeddings)
        await pg.update_vector_refs(pg_record.id, vector_ids)

        # 3. Graph DB
        graph_ids = await graph_db.insert_nodes(doc.nodes)
        await pg.update_graph_refs(pg_record.id, graph_ids)

    except Exception as e:
        await rollback(pg_record.id)
        raise
```

**Pros**:
- Simple de entender
- PostgreSQL como source of truth
- Control total del flujo

**Contras**:
- Rollback puede ser complejo
- No es atómico (ventana de inconsistencia)
- Lento para operaciones grandes

**Esfuerzo estimado**: Medio

---

### Opción B: Outbox Pattern + Event Bus

**Descripción**: Escribir eventos en una tabla outbox de PostgreSQL, procesarlos asincrónicamente.

```python
async def create_document(doc):
    async with pg.transaction():
        # 1. Insertar documento
        pg_record = await pg.insert_document(doc)

        # 2. Insertar eventos en outbox
        await pg.insert_outbox_event("SYNC_VECTOR", {"doc_id": pg_record.id})
        await pg.insert_outbox_event("SYNC_GRAPH", {"doc_id": pg_record.id})

# Worker procesa outbox
async def process_outbox():
    events = await pg.get_pending_events()
    for event in events:
        if event.type == "SYNC_VECTOR":
            await sync_to_vector_db(event.payload)
        elif event.type == "SYNC_GRAPH":
            await sync_to_graph_db(event.payload)
        await pg.mark_event_processed(event.id)
```

**Pros**:
- Garantiza que eventos no se pierden (en PostgreSQL)
- Reintentos automáticos
- Desacopla operaciones

**Contras**:
- Consistencia eventual (delay)
- Requiere worker/scheduler
- Más componentes

**Esfuerzo estimado**: Alto

---

### Opción C: Saga Pattern

**Descripción**: Cada operación es una saga con pasos compensatorios definidos.

```python
class CreateDocumentSaga:
    steps = [
        SagaStep(
            action=insert_to_postgres,
            compensation=delete_from_postgres
        ),
        SagaStep(
            action=insert_to_vector_db,
            compensation=delete_from_vector_db
        ),
        SagaStep(
            action=insert_to_graph_db,
            compensation=delete_from_graph_db
        ),
    ]

    async def execute(self, doc):
        completed = []
        for step in self.steps:
            try:
                result = await step.action(doc)
                completed.append((step, result))
            except Exception:
                # Compensar en orden inverso
                for s, r in reversed(completed):
                    await s.compensation(r)
                raise
```

**Pros**:
- Manejo explícito de compensaciones
- Patrón conocido para transacciones distribuidas
- Extensible

**Contras**:
- Complejo de implementar bien
- Compensaciones pueden fallar también
- Overhead de coordinación

**Esfuerzo estimado**: Alto

---

### Opción D: PostgreSQL como Source of Truth + Sync Jobs

**Descripción**: PostgreSQL es la única fuente de verdad. Jobs periódicos sincronizan Vector y Graph DB.

```python
# Toda la lógica en PostgreSQL
async def create_document(doc):
    await pg.insert_document(doc)
    await pg.insert_chunks(doc.chunks)
    await pg.insert_entities(doc.entities)  # Sin enviar a Graph aún
    await pg.mark_document_pending_sync()

# Job de sincronización (cada N segundos o por evento)
async def sync_job():
    pending = await pg.get_pending_sync()
    for doc in pending:
        await vector_db.upsert(doc.embeddings)
        await graph_db.upsert(doc.entities)
        await pg.mark_document_synced(doc.id)
```

**Pros**:
- Modelo mental simple
- PostgreSQL garantiza durabilidad
- Fácil de debuggear (todo en PostgreSQL)

**Contras**:
- Delay en disponibilidad para búsqueda
- Requiere job scheduler
- Puede haber drift si job falla

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Secuencial | Outbox | Saga | PG + Jobs |
|----------|------|------------|--------|------|-----------|
| Simplicidad | 2 | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ |
| Consistencia | 3 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Recuperación fallos | 3 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Rendimiento | 2 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Debuggability | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Total ponderado** | | 27 | 32 | 29 | 33 |

## 5. Preguntas Abiertas

- [ ] ¿Cuál es el delay aceptable para que un documento esté disponible para búsqueda?
- [ ] ¿Se necesita notificación cuando la sincronización completa?
- [ ] ¿Cómo manejar conflictos si el mismo documento se edita concurrentemente?
- [ ] ¿Se requiere reconciliación periódica (verificar consistencia)?
- [ ] ¿Qué pasa si Vector/Graph DB está temporalmente no disponible?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Eventual Consistency](https://www.allthingsdistributed.com/2008/12/eventually_consistent.html)
- [Change Data Capture](https://debezium.io/documentation/reference/stable/tutorial.html)
