---
kind: entity
aliases: [Node, Nodo]
status: draft
---

# GraphNode

## Descripción

Un [[GraphNode]] es un nodo del grafo de conocimiento, producido al indexar un [[KDDDocument]]. Cada nodo representa un artefacto KDD concreto (una entidad, un command, una regla de negocio, etc.) con sus campos indexados extraídos del contenido del documento fuente.

El nodo almacena los campos indexados según el `kind` del documento de origen, siguiendo la tabla de "Nodos del grafo" definida en el PRD. Por ejemplo, un nodo de tipo `entity` incluye `description`, `attributes`, `relations`, `invariants` y `state_machine`; mientras que un nodo de tipo `command` incluye `purpose`, `input_params`, `preconditions`, `postconditions` y `errors`.

## Atributos

| Atributo | Tipo | Requerido | Descripción |
|----------|------|-----------|-------------|
| `id` | `string` | Sí | Identificador compuesto `{Kind}:{DocumentId}` (e.g. `Entity:Pedido`, `CMD:CMD-001`) |
| `kind` | `KDDKind` | Sí | Tipo de artefacto KDD del documento de origen |
| `source_file` | `string` | Sí | Ruta relativa al fichero fuente |
| `source_hash` | `string` | Sí | Hash del documento de origen al momento de la extracción |
| `layer` | `KDDLayer` | Sí | Capa KDD (`01-domain`, `02-behavior`, etc.) |
| `status` | `string` | Sí | Status del artefacto KDD (`draft`, `review`, `approved`, `deprecated`) |
| `aliases` | `list[string]` | No | Nombres alternativos del artefacto |
| `domain` | `string` | No | Dominio en estructura multi-domain |
| `indexed_fields` | `dict` | Sí | Campos indexados específicos del `kind` (ver tabla del PRD) |
| `indexed_at` | `datetime` | Sí | Timestamp de la extracción |

## Relaciones

| Relación | Cardinalidad | Destino | Descripción |
|----------|-------------|---------|-------------|
| originado por | 1:1 | [[KDDDocument]] | El documento fuente que produjo este nodo (relación 1:1) |
| conectado por | N:N | [[GraphEdge]] | Edges donde este nodo es origen o destino |
| registrado en | N:1 | [[IndexManifest]] | Manifiesto que contiene este nodo |

## Invariantes

- El `id` es único dentro de un [[IndexManifest]]. La unicidad se garantiza por la combinación `{Kind}:{DocumentId}`.
- Los `indexed_fields` deben contener al menos los campos requeridos según la tabla de nodos del PRD para el `kind` correspondiente.
- Si el `source_hash` del nodo difiere del `source_hash` actual del [[KDDDocument]], el nodo está desactualizado y debe re-extraerse.
- El `layer` del nodo debe coincidir con la capa del documento de origen.
