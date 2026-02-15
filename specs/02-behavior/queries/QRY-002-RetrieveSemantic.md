---
id: QRY-002
kind: query
title: RetrieveSemantic
status: draft
---

# QRY-002 — RetrieveSemantic

## Purpose

Ejecutar una búsqueda semántica sobre los [[Embedding|embeddings]] del índice, encontrando los fragmentos de [[KDDDocument|documentos]] más similares al texto de la consulta. Devuelve los documentos ordenados por relevancia semántica.

Corresponde al endpoint `POST /v1/retrieve/search` del API de retrieval.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `query_text` | `string` | Sí | Texto de búsqueda en lenguaje natural. Mínimo 3 caracteres |
| `include_kinds` | `list[string]` | No | Filtro por `kind` de documento. Default: todos |
| `include_layers` | `list[string]` | No | Filtro por capa KDD. Default: todas |
| `min_score` | `float` | No | Score mínimo de similitud (0.0–1.0). Default `0.7` |
| `limit` | `int` | No | Máximo de resultados. Default `10`. Rango: 1–100 |

## Output

```yaml
results:
  - document_id: "UC-001"
    document_kind: "use-case"
    node_id: "UC:UC-001"
    section_path: "flujo_principal.paso_2"
    score: 0.92
    snippet: "El sistema aplica BR-DOCUMENT-001 para determinar el kind..."
    raw_text: "..."       # párrafo original completo
  - document_id: "BR-DOCUMENT-001"
    document_kind: "business-rule"
    node_id: "BR:BR-DOCUMENT-001"
    section_path: "declaracion"
    score: 0.87
    snippet: "Dado un fichero dentro de /specs, el sistema debe determinar..."
    raw_text: "..."
total_results: 2
embedding_model: "nomic-embed-text-v1.5"
```

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `QUERY_TOO_SHORT` | `query_text` tiene menos de 3 caracteres | "Query text must be at least 3 characters" |
| `NO_EMBEDDINGS` | El índice es L1 (sin embeddings) | "Semantic search requires index level ≥ L2" |
| `INVALID_SCORE_RANGE` | `min_score` fuera de 0.0–1.0 | "min_score must be between 0.0 and 1.0" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
