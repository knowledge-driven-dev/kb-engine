---
id: EVT-Index-MergeCompleted
kind: event
title: "Index MergeCompleted"
status: draft
---

# EVT-Index-MergeCompleted

## Descripción

Se emite cuando el proceso de merge de índices ha completado exitosamente, produciendo un [[IndexManifest]] unificado con el grafo consolidado de todos los desarrolladores. A partir de este momento, el índice mergeado está disponible para consultas de retrieval.

Si el merge detectó conflictos (mismo nodo modificado por diferentes desarrolladores), se resuelven según [[BR-MERGE-001]] y se reportan en el payload como `conflicts_resolved`.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `merge_id` | `uuid` | Identificador de la operación de merge (correlaciona con [[EVT-Index-MergeRequested]]) |
| `merged_manifest_id` | `string` | ID del [[IndexManifest]] resultante |
| `source_count` | `int` | Número de índices mergeados |
| `total_nodes` | `int` | Número total de nodos en el índice unificado |
| `total_edges` | `int` | Número total de edges en el índice unificado |
| `total_embeddings` | `int` | Número total de embeddings en el índice unificado |
| `conflicts_resolved` | `int` | Número de conflictos detectados y resueltos automáticamente |
| `duration_ms` | `int` | Tiempo total del merge en milisegundos |
| `completed_at` | `datetime` | Timestamp de finalización |

## Productor

- Motor de merge del servidor

## Consumidores

- API de retrieval: actualiza el índice activo para servir consultas sobre el grafo unificado
- Logger: registra métricas del merge para monitoreo
