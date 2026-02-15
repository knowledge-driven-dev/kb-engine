---
kind: entity
aliases: [Manifest, Manifiesto]
status: draft
---

# IndexManifest

## Descripción

Un [[IndexManifest]] contiene la metadata completa de un índice generado por un desarrollador. Se serializa como `manifest.json` en la raíz de `.kdd-index/` y funciona como punto de entrada para entender el contenido, versión y configuración de un índice.

El manifiesto es la pieza clave para el merge en servidor: cuando múltiples desarrolladores hacen push de sus `.kdd-index/`, el servidor usa los manifiestos para determinar compatibilidad (versión del schema, modelo de embeddings, estructura de dominios) antes de ejecutar el merge.

## Atributos

| Atributo | Tipo | Requerido | Descripción |
|----------|------|-----------|-------------|
| `version` | `string` | Sí | Versión del schema del índice (semver, e.g. `1.0.0`) |
| `kdd_version` | `string` | Sí | Versión del modelo KDD usado (e.g. `1.0`) |
| `embedding_model` | `string` | No | Identificador del modelo de embeddings (solo si nivel ≥ L2) |
| `embedding_dimensions` | `int` | No | Dimensiones de los vectores (solo si nivel ≥ L2) |
| `indexed_at` | `datetime` | Sí | Timestamp de la última indexación |
| `indexed_by` | `string` | Sí | Identificador del desarrollador que generó el índice |
| `structure` | `string` | Sí | Estructura del proyecto: `single-domain` o `multi-domain` |
| `index_level` | `IndexLevel` | Sí | Nivel de indexación ejecutado: `L1`, `L2` o `L3` |
| `stats` | `IndexStats` | Sí | Estadísticas del índice |
| `stats.nodes` | `int` | Sí | Número total de nodos |
| `stats.edges` | `int` | Sí | Número total de edges |
| `stats.embeddings` | `int` | Sí | Número total de embeddings (0 si solo L1) |
| `stats.enrichments` | `int` | Sí | Número total de enrichments (0 si < L3) |
| `domains` | `list[string]` | No | Lista de dominios indexados (solo en multi-domain) |
| `git_commit` | `string` | No | Hash del commit de Git al momento de indexar |

## Relaciones

| Relación | Cardinalidad | Destino | Descripción |
|----------|-------------|---------|-------------|
| contiene nodos | 1:N | [[GraphNode]] | Todos los nodos del índice |
| contiene edges | 1:N | [[GraphEdge]] | Todos los edges del índice |
| contiene embeddings | 1:N | [[Embedding]] | Todos los embeddings del índice |
| contiene documentos | 1:N | [[KDDDocument]] | Todos los documentos indexados |

## Invariantes

- El `version` debe seguir semver. Dos índices con `version` major diferente no son mergeables.
- Si `index_level` es `L1`, `embedding_model` y `embedding_dimensions` deben estar ausentes o ser nulos. Si es `L2` o `L3`, ambos son requeridos.
- Las `stats` deben reflejar los conteos reales de artefactos en el índice.
- Si `structure` es `multi-domain`, `domains` no puede estar vacío.
- El `indexed_by` identifica de forma única al desarrollador para el proceso de merge.
