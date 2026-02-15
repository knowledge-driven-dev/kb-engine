---
id: EVT-KDDDocument-Indexed
kind: event
title: "KDDDocument Indexed"
status: draft
---

# EVT-KDDDocument-Indexed

## Descripción

Se emite cuando un [[KDDDocument]] ha completado todo el pipeline de indexación: el [[GraphNode]] ha sido generado, los [[GraphEdge|edges]] han sido extraídos, y los [[Embedding|embeddings]] (si el nivel de indexación es ≥ L2) han sido creados y almacenados en `.kdd-index/`.

Este evento marca la transición `parsing → indexed` en el ciclo de vida del documento. A partir de este momento el documento es consultable por los flujos de retrieval.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | `string` | ID del documento indexado |
| `source_path` | `string` | Ruta relativa del fichero |
| `kind` | `KDDKind` | Tipo de artefacto KDD |
| `node_id` | `string` | ID del [[GraphNode]] generado (e.g. `Entity:Pedido`) |
| `edge_count` | `int` | Número de [[GraphEdge|edges]] generados |
| `embedding_count` | `int` | Número de [[Embedding|embeddings]] generados (0 si nivel L1) |
| `index_level` | `IndexLevel` | Nivel de indexación ejecutado (`L1`, `L2`, `L3`) |
| `duration_ms` | `int` | Tiempo total de indexación del documento en milisegundos |
| `indexed_at` | `datetime` | Timestamp de finalización |

## Productor

- Pipeline de indexación local (al completar todas las fases para un documento)

## Consumidores

- [[IndexManifest]]: actualiza estadísticas (`stats.nodes`, `stats.edges`, `stats.embeddings`)
- Logger de indexación: registra el resultado para métricas de rendimiento ([[REQ-001-Performance]])
