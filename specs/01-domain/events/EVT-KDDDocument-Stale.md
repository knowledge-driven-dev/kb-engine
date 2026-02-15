---
id: EVT-KDDDocument-Stale
kind: event
title: "KDDDocument Stale"
status: draft
---

# EVT-KDDDocument-Stale

## Descripción

Se emite cuando se detecta que un [[KDDDocument]] previamente indexado ha sido modificado en el filesystem. La detección se basa en la comparación del `source_hash` almacenado con el hash actual del fichero.

Este evento marca la transición `indexed → stale` en el ciclo de vida del documento. Un documento `stale` mantiene su [[GraphNode]], [[GraphEdge|edges]] y [[Embedding|embeddings]] anteriores disponibles para consulta, pero se marca para re-indexación en el próximo ciclo.

La detección de staleness ocurre durante la indexación incremental ([[CMD-002-IndexIncremental]]) al procesar el `git diff` de los últimos cambios.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | `string` | ID del documento que ha quedado obsoleto |
| `source_path` | `string` | Ruta relativa del fichero |
| `previous_hash` | `string` | Hash almacenado (del momento de la última indexación) |
| `current_hash` | `string` | Hash actual del fichero en el filesystem |
| `detected_at` | `datetime` | Timestamp de detección del cambio |

## Productor

- Detector de cambios (componente que compara hashes o procesa `git diff`)

## Consumidores

- Pipeline de re-indexación: encola el documento para re-procesamiento
- Logger de indexación: registra documentos obsoletos para métricas de freshness (`index_staleness_seconds`)
