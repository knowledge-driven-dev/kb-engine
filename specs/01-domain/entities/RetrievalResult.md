---
kind: entity
aliases: [Result, Resultado]
status: draft
---

# RetrievalResult

## Descripción

Un [[RetrievalResult]] es la respuesta devuelta por el motor de retrieval al resolver una [[RetrievalQuery]]. Contiene la lista de [[GraphNode|nodos]] relevantes con sus scores, los [[GraphEdge|edges]] que los conectan (si la estrategia incluye expansión por grafo), y metadata sobre la resolución.

El resultado está diseñado para ser consumido directamente por agentes de IA: incluye el contenido indexado de cada nodo junto con el subgrafo de relaciones, permitiendo al agente entender no solo "qué" se encontró sino "cómo se relaciona".

## Atributos

| Atributo | Tipo | Requerido | Descripción |
|----------|------|-----------|-------------|
| `query_id` | `uuid` | Sí | ID de la [[RetrievalQuery]] que originó este resultado |
| `strategy` | `RetrievalStrategy` | Sí | Estrategia usada (copiada de la query para conveniencia) |
| `results` | `list[ScoredNode]` | Sí | Nodos encontrados con su score de relevancia |
| `results[].node_id` | `string` | Sí | ID del [[GraphNode]] (e.g. `Entity:Pedido`) |
| `results[].score` | `float` | Sí | Score de relevancia (0.0–1.0) |
| `results[].snippet` | `string` | No | Fragmento de texto más relevante del nodo |
| `results[].match_source` | `string` | Sí | Fuente del match: `semantic`, `graph`, `lexical`, `fusion` |
| `graph_expansion` | `list[GraphEdge]` | No | Subgrafo de edges que conectan los nodos del resultado |
| `total_nodes` | `int` | Sí | Número total de nodos en el resultado |
| `total_tokens` | `int` | No | Estimación de tokens del resultado (para control de context window) |
| `layer_violations` | `list[LayerViolation]` | No | Violaciones de capa detectadas en el subgrafo (si `respect_layers` estaba activo) |

## Relaciones

| Relación | Cardinalidad | Destino | Descripción |
|----------|-------------|---------|-------------|
| originado por | 1:1 | [[RetrievalQuery]] | La consulta que produjo este resultado |
| contiene nodos | N:N | [[GraphNode]] | Nodos incluidos en el resultado |
| contiene edges | N:N | [[GraphEdge]] | Edges del subgrafo expandido |

## Invariantes

- Los `results` están ordenados por `score` descendente.
- Si la query tenía `min_score`, todos los nodos en `results` tienen `score ≥ min_score`.
- Si la query tenía `limit`, `total_nodes ≤ limit`.
- Si la query tenía `respect_layers: true`, los nodos con violaciones de capa se excluyen de `results` pero se reportan en `layer_violations`.
- El `total_tokens` nunca excede el `max_tokens` de la query (si fue especificado).
