---
id: QRY-001
kind: query
title: RetrieveByGraph
status: draft
---

# QRY-001 — RetrieveByGraph

## Purpose

Ejecutar un traversal del grafo de conocimiento partiendo de un [[GraphNode]] raíz, siguiendo [[GraphEdge|edges]] según los tipos y profundidad especificados. Devuelve el subgrafo alcanzable desde el nodo raíz.

Corresponde al endpoint `GET /v1/retrieve/graph` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `root_node` | `string` | Sí | ID del nodo raíz (e.g. `Entity:KDDDocument`). Debe existir en el índice |
| `depth` | `int` | No | Profundidad máxima de traversal. Default `2`. Rango: 1–5 |
| `edge_types` | `list[string]` | No | Tipos de edge a seguir (e.g. `["EMITS", "ENTITY_RULE"]`). Default: todos |
| `include_kinds` | `list[string]` | No | Filtro por `kind` de nodo en resultados. Default: todos |
| `respect_layers` | `bool` | No | Si `true`, excluye edges marcados con `layer_violation`. Default `true` |

## Output

```yaml
center_node:
  id: "Entity:KDDDocument"
  kind: "entity"
  layer: "01-domain"
  indexed_fields: { ... }
related_nodes:
  - id: "BR:BR-DOCUMENT-001"
    kind: "business-rule"
    distance: 1          # saltos desde el nodo raíz
    indexed_fields: { ... }
  - id: "EVT:EVT-KDDDocument-Detected"
    kind: "event"
    distance: 1
    indexed_fields: { ... }
edges:
  - from_node: "Entity:KDDDocument"
    to_node: "BR:BR-DOCUMENT-001"
    edge_type: "ENTITY_RULE"
  - from_node: "Entity:KDDDocument"
    to_node: "EVT:EVT-KDDDocument-Detected"
    edge_type: "EMITS"
total_nodes: 3
total_edges: 2
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `NODE_NOT_FOUND` | El `root_node` no existe en el índice | "Node not found: {root_node}" |
| `INVALID_DEPTH` | `depth` fuera del rango 1–5 | "Depth must be between 1 and 5" |
| `INVALID_EDGE_TYPE` | Un tipo de edge no es reconocido | "Unknown edge type: {edge_type}" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
