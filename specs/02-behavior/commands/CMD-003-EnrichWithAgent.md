---
id: CMD-003
kind: command
title: EnrichWithAgent
status: draft
---

# CMD-003 — EnrichWithAgent

## Purpose

Enriquecer un [[GraphNode]] existente usando el agente de IA del desarrollador (Claude, Codex, etc.). El agente analiza el [[KDDDocument]] original y genera enrichments: resúmenes mejorados, relaciones implícitas no expresadas en wiki-links, y análisis de impacto preliminar.

Este comando corresponde al nivel L3 (Enriquecido) del pipeline según [[BR-INDEX-001]] y es **completamente opcional**. Usa la licencia/API key del desarrollador.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `node_id` | `string` | Sí | ID del [[GraphNode]] a enriquecer (e.g. `Entity:Pedido`). Debe existir en el índice |
| `index_path` | `string` | No | Ruta a `.kdd-index/`. Default: `.kdd-index/` |
| `agent_provider` | `string` | No | Proveedor del agente: `anthropic`, `openai`. Default: detectado de la API key configurada |
| `api_key_env` | `string` | No | Variable de entorno con la API key. Default: `ANTHROPIC_API_KEY` o `OPENAI_API_KEY` |

## Preconditions

- El [[GraphNode]] referenciado por `node_id` existe en el índice.
- El [[KDDDocument]] fuente del nodo existe en el filesystem (para enviarlo al agente).
- Una API key válida está configurada en el entorno.
- El índice tiene nivel ≥ L2 (los enrichments se basan en los embeddings existentes).

## Postconditions

- Se ha generado un fichero de enrichment en `.kdd-index/enrichments/{document_id}.enrichment.json`.
- El enrichment contiene: resumen mejorado, relaciones implícitas descubiertas, análisis de impacto preliminar.
- Las relaciones implícitas descubiertas se han añadido como [[GraphEdge|edges]] adicionales al grafo (con `extraction_method: implicit`).
- Las `stats.enrichments` del [[IndexManifest]] se han incrementado.

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `NODE_NOT_FOUND` | El `node_id` no existe en el índice | "Node not found: {node_id}" |
| `DOCUMENT_NOT_FOUND` | El fichero fuente del nodo no existe | "Source document not found for node {node_id}" |
| `API_KEY_MISSING` | No se encontró API key configurada | "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY" |
| `AGENT_ERROR` | El agente devolvió un error | "Agent enrichment failed: {detail}" |
| `AGENT_TIMEOUT` | El agente no respondió en tiempo | "Agent enrichment timed out after {timeout_ms}ms" |
| `LOW_INDEX_LEVEL` | El índice es L1 (sin embeddings) | "Enrichment requires index level ≥ L2" |
