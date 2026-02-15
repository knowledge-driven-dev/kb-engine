---
id: QRY-003
kind: query
title: RetrieveHybrid
status: draft
---

# QRY-003 — RetrieveHybrid

## Purpose

Ejecutar una búsqueda híbrida que combina tres estrategias: semántica ([[QRY-002-RetrieveSemantic]]), traversal de grafo ([[QRY-001-RetrieveByGraph]]) y lexical (búsqueda por texto exacto). Los resultados de las tres fuentes se fusionan con un scoring combinado.

Esta es la query principal para agentes de IA — el punto de entrada recomendado para obtener contexto completo. Corresponde al endpoint `POST /v1/retrieve/context` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `query_text` | `string` | Sí | Texto de búsqueda en lenguaje natural. Mínimo 3 caracteres |
| `expand_graph` | `bool` | No | Si `true`, los resultados semánticos se expanden por grafo. Default `true` |
| `depth` | `int` | No | Profundidad de expansión por grafo. Default `2`. Rango: 1–5 |
| `include_kinds` | `list[string]` | No | Filtro por `kind` de nodo. Default: todos |
| `respect_layers` | `bool` | No | Si `true`, excluye resultados con violaciones de capa. Default `true` |
| `min_score` | `float` | No | Score mínimo tras fusion. Default `0.5` |
| `limit` | `int` | No | Máximo de resultados. Default `10`. Rango: 1–100 |
| `max_tokens` | `int` | No | Límite de tokens en la respuesta. Default `8000` |

## Output

```yaml
results:
  - node_id: "UC:UC-001"
    kind: "use-case"
    score: 0.95
    match_source: "fusion"    # semantic + graph
    snippet: "Indexar un documento KDD individual..."
    indexed_fields: { ... }
  - node_id: "BR:BR-DOCUMENT-001"
    kind: "business-rule"
    score: 0.88
    match_source: "semantic"
    snippet: "Dado un fichero dentro de /specs..."
    indexed_fields: { ... }
  - node_id: "EVT:EVT-KDDDocument-Indexed"
    kind: "event"
    score: 0.72
    match_source: "graph"     # alcanzado por expansión
    snippet: "Se emite cuando un KDDDocument ha completado..."
    indexed_fields: { ... }
graph_expansion:
  - from_node: "UC:UC-001"
    to_node: "BR:BR-DOCUMENT-001"
    edge_type: "UC_APPLIES_RULE"
  - from_node: "UC:UC-001"
    to_node: "CMD:CMD-001"
    edge_type: "UC_EXECUTES_CMD"
total_results: 3
total_tokens: 2450
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `QUERY_TOO_SHORT` | `query_text` tiene menos de 3 caracteres | "Query text must be at least 3 characters" |
| `NO_EMBEDDINGS` | El índice es L1 (sin embeddings); la búsqueda degrada a grafo + lexical | "No embeddings available, falling back to graph + lexical" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
| `TOKEN_LIMIT_EXCEEDED` | Los resultados exceden `max_tokens` antes de completar | "Results truncated at {max_tokens} tokens" |
