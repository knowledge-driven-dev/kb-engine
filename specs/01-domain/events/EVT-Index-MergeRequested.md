---
id: EVT-Index-MergeRequested
kind: event
title: "Index MergeRequested"
status: draft
---

# EVT-Index-MergeRequested

## Descripción

Se emite cuando el servidor recibe los artefactos de índice (`.kdd-index/`) de uno o más desarrolladores y se solicita un merge para producir un grafo unificado. Este evento inicia el proceso de merge descrito en [[UC-006-MergeIndex]].

Antes de ejecutar el merge, el sistema valida la compatibilidad de los [[IndexManifest|manifiestos]]: misma `version` major, mismo `embedding_model` (si aplica), y estructura compatible (`single-domain` / `multi-domain`).

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `merge_id` | `uuid` | Identificador único de esta operación de merge |
| `source_manifests` | `list[string]` | IDs de los manifiestos a mergear (uno por desarrollador) |
| `developer_ids` | `list[string]` | Identificadores de los desarrolladores cuyos índices se mergean |
| `target_version` | `string` | Versión del schema del índice resultante |
| `requested_at` | `datetime` | Timestamp de la solicitud |
| `requested_by` | `string` | Identificador del usuario o sistema que solicitó el merge |

## Productor

- Servidor de merge (al recibir push de `.kdd-index/` via [[CMD-005-SyncIndex]])

## Consumidores

- Motor de merge: inicia la reconciliación de nodos, edges y embeddings según [[BR-MERGE-001]]
