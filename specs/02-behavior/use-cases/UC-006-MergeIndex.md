---
id: UC-006
kind: use-case
title: MergeIndex
version: 1
status: draft
actor: Server
---

# UC-006 — MergeIndex

## Descripción

El servidor compartido recibe los artefactos de índice (`.kdd-index/`) de múltiples desarrolladores y ejecuta un merge para producir un [[IndexManifest]] unificado con el grafo consolidado. El índice mergeado es el que alimenta el API de retrieval compartido.

## Actores

- **Server**: Proceso del servidor que ejecuta el merge automáticamente al recibir nuevos índices.
- **Admin**: Puede forzar un merge manual o configurar la estrategia de conflictos.

## Precondiciones

- Al menos dos índices de desarrolladores están disponibles en el servidor (recibidos via [[UC-007-SyncIndex]]).
- Los [[IndexManifest|manifiestos]] son compatibles según [[BR-MERGE-001]].

## Flujo Principal

1. El servidor detecta que hay nuevos índices pendientes de merge (recibidos via push).
2. El sistema lee los [[IndexManifest|manifiestos]] de cada índice y valida compatibilidad: misma `version` major, mismo `embedding_model`, misma `structure` ([[BR-MERGE-001]]).
3. Se emite [[EVT-Index-MergeRequested]] con los manifiestos participantes.
4. El sistema recorre los [[GraphNode|nodos]] de todos los índices:
   - Nodos presentes en un solo índice: se copian directamente.
   - Nodos con mismo `source_hash` en todos los índices: se toma una copia (son idénticos).
   - Nodos con diferente `source_hash`: conflicto → last-write-wins por `indexed_at` más reciente ([[BR-MERGE-001]]).
   - Nodos ausentes en un índice pero presentes en otro: delete-wins.
5. El sistema mergea los [[GraphEdge|edges]] por unión, eliminando duplicados (`from_node` + `to_node` + `edge_type`). Los edges de nodos eliminados se eliminan en cascada.
6. El sistema reemplaza los [[Embedding|embeddings]] de nodos en conflicto por los del nodo ganador.
7. El sistema genera un nuevo [[IndexManifest]] con `stats` consolidadas.
8. Se emite [[EVT-Index-MergeCompleted]] con métricas del merge.
9. El índice mergeado reemplaza al anterior como índice activo del API de retrieval.

## Flujos Alternativos

### FA-1: Manifiestos incompatibles
- En el paso 2, si los manifiestos tienen `version` major diferente, `embedding_model` diferente o `structure` diferente, el merge se rechaza con error. Se notifica a los desarrolladores afectados.

### FA-2: Estrategia fail_on_conflict
- Si el admin configuró `conflict_strategy: fail_on_conflict` y hay nodos en conflicto en el paso 4, el merge aborta sin producir índice mergeado.

### FA-3: Un solo índice
- Si solo hay un índice disponible, el merge es trivial: se copia como índice activo sin modificaciones.

## Excepciones

### EX-1: Manifiestos incompatibles
- Se emite error `INCOMPATIBLE_VERSION`, `INCOMPATIBLE_EMBEDDING_MODEL` o `INCOMPATIBLE_STRUCTURE`. El merge no se ejecuta.

### EX-2: Error de escritura
- Si no se puede escribir el índice mergeado, se emite error `OUTPUT_WRITE_FAILED`. El índice anterior permanece activo.

## Postcondiciones

- Un [[IndexManifest]] unificado está disponible como índice activo del API de retrieval.
- Todos los conflictos han sido resueltos según [[BR-MERGE-001]].
- Las `stats` reflejan los conteos reales del índice mergeado.

## Reglas Aplicadas

- [[BR-MERGE-001]] — Merge Conflict Resolution: last-write-wins, delete-wins, validación de compatibilidad.

## Comandos Ejecutados

- [[CMD-004-MergeIndex]] — Comando que implementa el merge.
