---
id: CMD-004
kind: command
title: MergeIndex
status: draft
---

# CMD-004 — MergeIndex

## Purpose

Mergear los índices (`.kdd-index/`) de múltiples desarrolladores en un índice unificado en el servidor compartido. El merge produce un [[IndexManifest]] consolidado con el grafo completo de [[GraphNode|nodos]], [[GraphEdge|edges]] y [[Embedding|embeddings]] de todos los contribuidores.

Los conflictos se resuelven según [[BR-MERGE-001]] (last-write-wins por nodo, delete-wins para eliminaciones).

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `source_indices` | `list[string]` | Sí | Rutas a los directorios `.kdd-index/` de cada desarrollador. Mínimo 2 |
| `output_path` | `string` | Sí | Ruta donde se escribirá el índice mergeado |
| `conflict_strategy` | `string` | No | Estrategia de resolución: `last_write_wins` (default), `fail_on_conflict` |

## Preconditions

- Cada ruta en `source_indices` contiene un [[IndexManifest]] válido.
- Los manifiestos son compatibles: misma `version` major, mismo `embedding_model`, misma `structure` ([[BR-MERGE-001]]).
- El directorio `output_path` existe o puede crearse.

## Postconditions

- Se emite [[EVT-Index-MergeRequested]] al inicio.
- Los nodos sin conflicto se copian al índice resultante.
- Los nodos en conflicto se resuelven según `conflict_strategy` y [[BR-MERGE-001]].
- Los edges se mergean por unión, eliminando duplicados exactos.
- Los embeddings del nodo ganador (en conflictos) reemplazan a los del perdedor.
- Los nodos eliminados en cualquier índice se eliminan del resultado (delete-wins), con cascada de edges y embeddings.
- Se genera un nuevo [[IndexManifest]] con `stats` consolidadas.
- Se emite [[EVT-Index-MergeCompleted]] con métricas del merge.

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `INSUFFICIENT_SOURCES` | Menos de 2 índices proporcionados | "Merge requires at least 2 source indices" |
| `MANIFEST_NOT_FOUND` | Un directorio no contiene manifest.json | "No manifest found in {path}" |
| `INCOMPATIBLE_VERSION` | Version major difiere entre manifiestos | "Incompatible index versions: {v1} vs {v2}" |
| `INCOMPATIBLE_EMBEDDING_MODEL` | Modelos de embeddings diferentes | "Incompatible embedding models: {m1} vs {m2}" |
| `INCOMPATIBLE_STRUCTURE` | Single-domain vs multi-domain | "Cannot merge single-domain with multi-domain indices" |
| `CONFLICT_REJECTED` | `fail_on_conflict` y hay conflictos | "Merge aborted: {n} conflicts detected" |
| `OUTPUT_WRITE_FAILED` | No se puede escribir en `output_path` | "Cannot write to output path: {output_path}" |
