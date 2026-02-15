---
id: QRY-005
kind: query
title: RetrieveCoverage
status: draft
---

# QRY-005 — RetrieveCoverage

## Purpose

Validar la cobertura de un [[GraphNode]] según las reglas de governance KDD. Dado un nodo, determinar qué artefactos relacionados **deberían existir** según su `kind` y cuáles faltan. Por ejemplo, una entidad debería tener al menos un evento, al menos una regla de negocio, y ser referenciada por al menos un caso de uso.

Corresponde al endpoint `GET /v1/retrieve/coverage` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `node_id` | `string` | Sí | ID del nodo a analizar (e.g. `Entity:KDDDocument`). Debe existir |

## Output

```yaml
analyzed_node:
  id: "Entity:KDDDocument"
  kind: "entity"
required:
  - category: "events"
    description: "Al menos un evento de dominio"
    edge_type: "EMITS"
    status: "covered"          # covered | missing | partial
    found: ["EVT:EVT-KDDDocument-Detected", "EVT:EVT-KDDDocument-Indexed"]
  - category: "business_rules"
    description: "Al menos una regla de negocio"
    edge_type: "ENTITY_RULE"
    status: "covered"
    found: ["BR:BR-DOCUMENT-001"]
  - category: "use_cases"
    description: "Referenciada por al menos un caso de uso"
    edge_type: "WIKI_LINK"
    status: "covered"
    found: ["UC:UC-001"]
  - category: "requirements"
    description: "Trazada a al menos un requirement"
    edge_type: "REQ_TRACES_TO"
    status: "missing"
    found: []
present: 3
missing: 1
coverage_percent: 75.0
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `NODE_NOT_FOUND` | El `node_id` no existe en el índice | "Node not found: {node_id}" |
| `UNKNOWN_KIND` | El `kind` del nodo no tiene reglas de cobertura definidas | "No coverage rules defined for kind: {kind}" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
