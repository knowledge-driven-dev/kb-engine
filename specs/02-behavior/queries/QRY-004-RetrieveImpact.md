---
id: QRY-004
kind: query
title: RetrieveImpact
status: draft
---

# QRY-004 — RetrieveImpact

## Purpose

Dado un [[GraphNode]], analizar el impacto de un cambio potencial en ese nodo. Devuelve todos los nodos afectados directa e indirectamente, los scenarios BDD que deberían re-ejecutarse, y la cadena de dependencias.

Corresponde al endpoint `GET /v1/retrieve/impact` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `node_id` | `string` | Sí | ID del nodo a analizar (e.g. `Entity:KDDDocument`). Debe existir |
| `change_type` | `string` | No | Tipo de cambio: `modify_attribute`, `add_attribute`, `remove`, `rename`. Default `modify_attribute` |
| `depth` | `int` | No | Profundidad máxima de propagación. Default `3`. Rango: 1–5 |

## Output

```yaml
analyzed_node:
  id: "Entity:KDDDocument"
  kind: "entity"
directly_affected:
  - id: "BR:BR-DOCUMENT-001"
    kind: "business-rule"
    edge_type: "ENTITY_RULE"
    impact: "La regla referencia directamente a KDDDocument"
  - id: "CMD:CMD-001"
    kind: "command"
    edge_type: "WIKI_LINK"
    impact: "El command opera sobre KDDDocument"
transitively_affected:
  - id: "UC:UC-001"
    kind: "use-case"
    path: ["Entity:KDDDocument", "CMD:CMD-001", "UC:UC-001"]
    edge_types: ["WIKI_LINK", "UC_EXECUTES_CMD"]
    impact: "El UC ejecuta CMD-001 que opera sobre KDDDocument"
scenarios_to_rerun:
  - feature: "index-entity.feature"
    scenario: "SCN-IndexEntity-001"
    reason: "Valida indexación de entidades"
total_directly_affected: 2
total_transitively_affected: 1
total_scenarios: 1
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `NODE_NOT_FOUND` | El `node_id` no existe en el índice | "Node not found: {node_id}" |
| `INVALID_CHANGE_TYPE` | `change_type` no reconocido | "Unknown change type: {change_type}" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
