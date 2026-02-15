---
id: BR-EMBEDDING-001
kind: business-rule
title: Embedding Strategy
category: validation
severity: medium
status: draft
---

# BR-EMBEDDING-001 — Embedding Strategy

## Declaración

Para cada [[KDDDocument]] indexado, el sistema determina qué secciones reciben [[Embedding|embeddings]] según el `kind` del documento. Solo las secciones con contenido semánticamente rico (prosa descriptiva, flujos, declaraciones) se embeben. Las secciones puramente estructurales (tablas de atributos, listas de parámetros) no se embeben.

Dentro de cada sección embebible, se aplica **chunking jerárquico por párrafos**: cada párrafo produce un [[Embedding]] individual cuyo texto se enriquece con resúmenes de las secciones padre para preservar el contexto del documento.

### Tabla de decisión: secciones embebibles por `kind`

| `kind` | Secciones embebibles | Secciones NO embebibles |
|--------|---------------------|------------------------|
| `entity` | `## Descripción` | `## Atributos`, `## Ciclo de Vida`, `## Relaciones`, `## Invariantes` |
| `event` | — (sin embeddings) | Todas |
| `business-rule` | `## Declaración`, `## Cuándo aplica` | `## Por qué existe`, `## Qué pasa si se incumple`, `## Ejemplos` |
| `business-policy` | `## Declaración` | `## Parámetros`, `## Cuándo aplica`, `## Qué pasa si se incumple` |
| `cross-policy` | `## Propósito`, `## Declaración` | `## Formalización EARS`, `## Comportamiento Estándar` |
| `command` | `## Purpose` | `## Input`, `## Preconditions`, `## Postconditions`, `## Possible Errors` |
| `query` | `## Purpose` | `## Input`, `## Output`, `## Possible Errors` |
| `process` | `## Participantes`, `## Pasos` | `## Diagrama` (mermaid) |
| `use-case` | `## Descripción`, `## Flujo Principal` | `## Actores`, `## Precondiciones`, `## Postcondiciones`, `## Reglas Aplicadas`, `## Comandos Ejecutados` |
| `ui-view` | `## Descripción`, `## Comportamiento` | `## Layout`, `## Componentes`, `## Estados` |
| `ui-component` | `## Descripción` | Todas las demás |
| `requirement` | `## Descripción` | `## Criterios de Aceptación`, `## Trazabilidad` |
| `objective` | `## Objetivo` | `## Actor`, `## Criterios de éxito` |
| `prd` | `## Problema / Oportunidad` | Todas las demás |
| `adr` | `## Contexto`, `## Decisión` | `## Consecuencias` |

### Reglas de chunking jerárquico

1. Cada párrafo dentro de una sección embebible produce un chunk independiente.
2. El texto que se embebe (`context_text`) se construye concatenando:
   - Línea de identidad: `[{kind}: {document_id}]`
   - Resumen de cada sección ancestro (del heading más general al más específico)
   - Texto del párrafo actual (`raw_text`)
3. Si un párrafo tiene menos de 20 palabras, se fusiona con el párrafo siguiente.
4. Las tablas dentro de secciones embebibles se tratan como un solo chunk por tabla (cada fila no es un chunk independiente).

## Por qué existe

La búsqueda semántica requiere que los vectores representen contenido con carga semántica. Embeber tablas de parámetros o diagramas mermaid produce vectores de baja calidad que degradan la precisión del retrieval. Al mismo tiempo, el chunking jerárquico evita que fragmentos cortos pierdan su contexto dentro del documento.

## Cuándo aplica

Durante la fase de generación de embeddings del pipeline de indexación (nivel L2 o superior), después de que el [[KDDDocument]] haya sido parseado exitosamente ([[EVT-KDDDocument-Parsed]]).

## Qué pasa si se incumple

- Si se embeben secciones no declaradas en esta regla, se producen vectores de baja calidad que degradan la precisión de la búsqueda semántica (SLO: ≥90% precision).
- Si se omite una sección embebible, cierto contenido queda invisible a la búsqueda semántica (solo accesible por grafo o lexical).

## Ejemplos

**Entity `Pedido.md` — chunking de `## Descripción`:**
```
Sección embebible: ## Descripción (3 párrafos)

Chunk 0 context_text:
  [entity: Pedido] >
  [Descripción] >
  "Representa un pedido de compra realizado por un Usuario..."

Chunk 1 context_text:
  [entity: Pedido] >
  [Descripción] >
  "El pedido tiene un ciclo de vida que va desde borrador..."

Chunk 2 context_text:
  [entity: Pedido] >
  [Descripción] >
  "Cada pedido contiene una o más líneas con productos..."
```

**Event `EVT-KDDDocument-Indexed.md` — sin embeddings:**
```
kind: event → no tiene secciones embebibles
→ 0 embeddings generados
→ Solo accesible por búsqueda de grafo o lexical
```
