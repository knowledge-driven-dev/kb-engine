---
id: QRY-007
kind: query
title: RetrieveContext
status: draft
---

# QRY-007 — RetrieveContext

## Purpose

Amplificador de contexto: dado un conjunto de hints (file paths, entity names, keywords), devuelve los artefactos KDD relevantes que un agente debería conocer antes de modificar código. No es solo business rules — es **todo artefacto que actúe como restricción o guía**: business rules, policies, invariantes de entidades, preconditions/postconditions de commands, flujos de use cases.

Priorizados por tipo: restricciones duras primero, contexto de comportamiento después.

El mecanismo es **pull, no push**: el agente (o un hook pre-prompt) llama explícitamente a `kdd_context` antes de actuar.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `hints` | `string[]` | Sí | File paths, entity names, keywords (e.g. `["pedido.ts", "checkout"]`). Min 1 |
| `depth` | `number` | No | Profundidad de traversal en el grafo. Default `1`. Rango: 1–3 |
| `max_tokens` | `number` | No | Budget de tokens para el output. Default `4000` |

## Output

```yaml
constraints:
  - node_id: "BR:BR-PRECIO-001"
    kind: "business-rule"
    content: "El precio final de un pedido debe calcularse como..."
    source_file: "01-domain/rules/BR-PRECIO-001.md"
    reached_via: "Entity:Pedido -> ENTITY_RULE -> BR:BR-PRECIO-001"
  - node_id: "BP:BP-DESCUENTO-001"
    kind: "business-policy"
    content: "Los descuentos aplicables se configuran por..."
    source_file: "01-domain/policies/BP-DESCUENTO-001.md"
    reached_via: "Entity:Pedido -> ENTITY_POLICY -> BP:BP-DESCUENTO-001"
behavior:
  - node_id: "UC:UC-001"
    kind: "use-case"
    content: "El usuario inicia el proceso de checkout..."
    source_file: "02-behavior/use-cases/UC-001-Checkout.md"
    reached_via: "Entity:Pedido -> UC_EXECUTES_CMD -> CMD:CMD-001 -> UC:UC-001"
resolved_entities:
  - node_id: "Entity:Pedido"
    matched_from: "pedido.ts"
    match_method: "basename"
warnings:
  - "No match found for hint: 'foo-bar'"
total_items: 3
total_tokens: 1250
```

## Algorithm

1. **Hint Resolution**: Cada hint se resuelve a nodos del grafo via exact match (node ID), basename match (file paths), o text search (keywords).
2. **Constraint Discovery**: Para cada nodo resuelto, se descubren restricciones via edges directos (ENTITY_RULE, ENTITY_POLICY, UC_APPLIES_RULE, UC_EXECUTES_CMD) y traversal opcional (depth > 1).
3. **Content Extraction**: Para cada nodo descubierto, se extrae texto relevante de `indexed_fields` según el kind.
4. **Sort & Token Budget**: Se ordenan por prioridad de kind (restricciones > entidades > comportamiento), se acumulan tokens, y se corta al llegar a `max_tokens`.

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `EMPTY_HINTS` | `hints` está vacío | "At least one hint is required" |
| `INDEX_UNAVAILABLE` | No hay índice cargado | "No index available for querying" |
