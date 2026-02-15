---
id: EVT-RetrievalQuery-Completed
kind: event
title: "RetrievalQuery Completed"
status: draft
---

# EVT-RetrievalQuery-Completed

## Descripción

Se emite cuando una [[RetrievalQuery]] ha sido resuelta exitosamente y se ha generado un [[RetrievalResult]]. Corresponde a la transición `resolving → completed` en el ciclo de vida de la consulta.

Este evento transporta las métricas de resolución necesarias para evaluar el cumplimiento del SLO de latencia (P95 < 300ms).

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `query_id` | `uuid` | Identificador de la consulta resuelta |
| `strategy` | `RetrievalStrategy` | Estrategia utilizada |
| `total_results` | `int` | Número de nodos en el resultado |
| `top_score` | `float` | Score más alto entre los resultados |
| `total_tokens` | `int` | Tokens estimados en la respuesta |
| `duration_ms` | `int` | Tiempo de resolución en milisegundos |
| `completed_at` | `datetime` | Timestamp de finalización |

## Productor

- Motor de resolución de queries (al completar la búsqueda y generar el resultado)

## Consumidores

- API de retrieval: envía la respuesta al caller
- Logger: registra `duration_ms` para la métrica `retrieval_duration_seconds` ([[REQ-001-Performance]])
