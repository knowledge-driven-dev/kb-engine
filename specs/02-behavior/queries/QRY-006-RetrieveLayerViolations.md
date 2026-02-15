---
id: QRY-006
kind: query
title: RetrieveLayerViolations
status: draft
---

# QRY-006 — RetrieveLayerViolations

## Purpose

Detectar y reportar todos los [[GraphEdge|edges]] del grafo que violan la regla de dependencias de capa KDD ([[BR-LAYER-001]]). Devuelve la lista de violaciones con detalle de los nodos implicados, sus capas y el tipo de edge.

Corresponde al endpoint `GET /v1/retrieve/layer-violations` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `include_kinds` | `list[string]` | No | Filtro por `kind` de nodo origen. Default: todos |
| `include_layers` | `list[string]` | No | Filtro por capa del nodo origen. Default: todas |

## Output

```yaml
violations:
  - from_node: "Entity:KDDDocument"
    from_layer: "01-domain"
    to_node: "UC:UC-001"
    to_layer: "02-behavior"
    edge_type: "WIKI_LINK"
    source_file: "specs/01-domain/entities/KDDDocument.md"
    section: "Descripción"
    explanation: "01-domain should not reference 02-behavior"
total_violations: 1
total_edges_analyzed: 132
violation_rate: 0.8   # porcentaje
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
