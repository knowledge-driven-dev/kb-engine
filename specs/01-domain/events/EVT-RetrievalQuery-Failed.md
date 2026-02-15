---
id: EVT-RetrievalQuery-Failed
kind: event
title: "RetrievalQuery Failed"
status: draft
---

# EVT-RetrievalQuery-Failed

## Descripción

Se emite cuando una [[RetrievalQuery]] no puede resolverse, ya sea por parámetros inválidos o por un error durante la resolución. Corresponde a las transiciones `received → failed` y `resolving → failed` en el ciclo de vida de la consulta.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `query_id` | `uuid` | Identificador de la consulta fallida |
| `strategy` | `RetrievalStrategy` | Estrategia solicitada |
| `error_code` | `string` | Código de error (e.g. `INVALID_PARAMS`, `NODE_NOT_FOUND`, `INDEX_UNAVAILABLE`, `TIMEOUT`) |
| `error_message` | `string` | Mensaje descriptivo del error |
| `phase` | `string` | Fase donde ocurrió el fallo: `validation` o `resolution` |
| `duration_ms` | `int` | Tiempo transcurrido hasta el fallo |
| `failed_at` | `datetime` | Timestamp del fallo |

## Productor

- Motor de resolución de queries (al detectar un error irrecuperable)
- Validador de parámetros (si la request es inválida antes de iniciar resolución)

## Consumidores

- API de retrieval: envía respuesta de error al caller
- Logger: registra el fallo para diagnóstico y alertas
