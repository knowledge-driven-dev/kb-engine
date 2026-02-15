---
id: UC-003
kind: use-case
title: EnrichWithAgent
version: 1
status: draft
actor: Developer
---

# UC-003 — EnrichWithAgent

## Descripción

El desarrollador solicita enriquecer un [[GraphNode]] existente usando su agente de IA personal (Claude, Codex, etc.). El agente analiza el [[KDDDocument]] original y genera enrichments: resúmenes mejorados, relaciones implícitas no expresadas en wiki-links, y análisis de impacto preliminar.

Este caso de uso es **completamente opcional** y corresponde al nivel L3 (Enriquecido) según [[BR-INDEX-001]]. Usa la licencia y API key del desarrollador.

## Actores

- **Developer**: Invoca el enriquecimiento explícitamente (`kb enrich <node_id>`).
- **Agente IA**: Claude, Codex u otro LLM que analiza el documento y genera enrichments.

## Precondiciones

- El [[GraphNode]] referenciado existe en el índice.
- El [[KDDDocument]] fuente del nodo existe en el filesystem.
- El índice tiene nivel ≥ L2 (los enrichments se basan en embeddings existentes).
- Una API key válida está configurada en el entorno del desarrollador.

## Flujo Principal

1. El desarrollador ejecuta `kb enrich <node_id>`.
2. El sistema localiza el [[GraphNode]] en el índice y recupera la ruta al [[KDDDocument]] fuente.
3. El sistema lee el contenido completo del documento fuente.
4. El sistema construye un prompt para el agente que incluye:
   - El contenido del documento.
   - Los [[GraphEdge|edges]] existentes del nodo (contexto del grafo).
   - Los nodos vecinos a 1 salto de profundidad (contexto relacional).
5. El sistema envía el prompt al agente IA configurado.
6. El agente devuelve:
   - Un resumen mejorado del documento.
   - Relaciones implícitas descubiertas (e.g. "este comando probablemente afecta a la entidad X aunque no la menciona explícitamente").
   - Análisis de impacto preliminar (qué otros artefactos podrían verse afectados por cambios en este nodo).
7. El sistema almacena el enrichment en `.kdd-index/enrichments/{document_id}.enrichment.json`.
8. Las relaciones implícitas descubiertas se añaden como [[GraphEdge|edges]] con `extraction_method: implicit`.
9. Se actualiza `stats.enrichments` del [[IndexManifest]].

## Flujos Alternativos

### FA-1: Enrichment ya existe
- En el paso 2, si ya existe un enrichment para el nodo, el sistema pregunta al desarrollador si desea regenerarlo. Si acepta, el enrichment anterior se sobrescribe.

### FA-2: Nodo sin vecinos
- En el paso 4, si el nodo no tiene edges ni vecinos, el prompt se envía sin contexto relacional. El agente trabaja solo con el contenido del documento.

## Excepciones

### EX-1: API key no configurada
- En el paso 5, si no hay API key válida, se emite error `API_KEY_MISSING`. El desarrollador debe configurarla.

### EX-2: Agente no responde
- En el paso 5, si el agente no responde en el timeout configurado, se emite error `AGENT_TIMEOUT`. El enrichment no se genera pero el índice existente no se ve afectado.

### EX-3: Respuesta inválida del agente
- En el paso 6, si la respuesta del agente no tiene el formato esperado, se emite error `AGENT_ERROR`. Se registra la respuesta raw para diagnóstico.

## Postcondiciones

- Un fichero de enrichment existe en `.kdd-index/enrichments/`.
- Los edges implícitos descubiertos están en `.kdd-index/edges/edges.jsonl` con `extraction_method: implicit`.
- El [[IndexManifest]] refleja el enrichment en sus stats.

## Reglas Aplicadas

- [[BR-INDEX-001]] — Index Level: valida que el índice es ≥ L2 antes de permitir enrichment.

## Comandos Ejecutados

- [[CMD-003-EnrichWithAgent]] — Comando que implementa este caso de uso.
