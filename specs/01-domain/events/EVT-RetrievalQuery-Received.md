---
id: EVT-RetrievalQuery-Received
kind: event
title: "RetrievalQuery Received"
status: draft
---

# EVT-RetrievalQuery-Received

## Descripción

Se emite cuando el API de retrieval recibe una nueva [[RetrievalQuery]] de un agente o desarrollador. En este punto, los parámetros de la consulta aún no han sido validados.

Corresponde a la transición `[*] → received` en el ciclo de vida de una [[RetrievalQuery]].

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `query_id` | `uuid` | Identificador único de la consulta |
| `strategy` | `RetrievalStrategy` | Estrategia solicitada (`graph`, `semantic`, `hybrid`, `impact`) |
| `query_text` | `string` | Texto de búsqueda (puede ser nulo para `graph` e `impact`) |
| `root_node` | `string` | Nodo raíz para traversal (puede ser nulo para `semantic`) |
| `caller` | `string` | Identificador del agente o usuario que envió la consulta |
| `received_at` | `datetime` | Timestamp de recepción |

## Productor

- API de retrieval (endpoint que recibe la request)

## Consumidores

- Motor de resolución de queries: valida parámetros y comienza la resolución
- Logger: registra la consulta para métricas de latencia ([[REQ-001-Performance]])
