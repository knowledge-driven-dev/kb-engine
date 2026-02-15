---
id: EVT-KDDDocument-Deleted
kind: event
title: "KDDDocument Deleted"
status: draft
---

# EVT-KDDDocument-Deleted

## Descripción

Se emite cuando un [[KDDDocument]] previamente indexado ha sido eliminado del filesystem. La detección ocurre durante la indexación incremental ([[CMD-002-IndexIncremental]]) cuando `git diff` reporta un fichero borrado, o durante un scan completo cuando un fichero registrado en el [[IndexManifest]] ya no existe.

Este evento desencadena la eliminación en cascada del [[GraphNode]], todos los [[GraphEdge|edges]] asociados y todos los [[Embedding|embeddings]] del documento. Corresponde a las transiciones `indexed → [*]` y `stale → [*]` en el ciclo de vida.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | `string` | ID del documento eliminado |
| `source_path` | `string` | Ruta relativa del fichero que existía |
| `node_id` | `string` | ID del [[GraphNode]] que será eliminado |
| `edge_count` | `int` | Número de edges que serán eliminados |
| `embedding_count` | `int` | Número de embeddings que serán eliminados |
| `deleted_at` | `datetime` | Timestamp de detección de la eliminación |

## Productor

- Detector de cambios (al procesar `git diff` o reconciliar con filesystem)

## Consumidores

- Pipeline de indexación: ejecuta la eliminación en cascada de nodo, edges y embeddings
- [[IndexManifest]]: actualiza estadísticas restando los artefactos eliminados
