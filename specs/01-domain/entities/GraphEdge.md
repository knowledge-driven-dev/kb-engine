---
kind: entity
aliases: [Edge, Relación, Arista]
status: draft
---

# GraphEdge

## Descripción

Un [[GraphEdge]] es una relación tipada y dirigida entre dos [[GraphNode|nodos]] del grafo de conocimiento. Los edges se extraen deterministamente del contenido de los [[KDDDocument|documentos]] KDD: wiki-links `[[...]]`, tablas de relaciones y secciones específicas de cada `kind`.

Un edge que conecta nodos de capas incompatibles según la regla de dependencias (04→03→02→01) se marca con `layer_violation: true`, permitiendo la detección de violaciones sin rechazar la indexación ([[BR-LAYER-001]]).

### Convención de nombres para `edge_type`

- **MAYÚSCULAS** (`SCREAMING_SNAKE_CASE`): relaciones **estructurales** extraídas automáticamente de la estructura KDD. Son fijas, predecibles y definidas por el motor. Ejemplo: `EMITS`, `UC_APPLIES_RULE`, `WIKI_LINK`.
- **minúsculas** (`snake_case`): relaciones **de negocio** definidas por el autor de la spec en el contenido (e.g. en la tabla `## Relaciones` de una entidad). Tienen semántica de dominio. Ejemplo: `aprueba`, `revisa`, `contiene`, `pertenece_a`.

### Relaciones estructurales (MAYÚSCULAS)

| EdgeType | Origen | Destino | Extracción |
|----------|--------|---------|------------|
| `WIKI_LINK` | Any | Any | `[[Target]]` en contenido (genérica, bidireccional) |
| `DOMAIN_RELATION` | Entity | Entity | Tabla `## Relaciones` + wiki-links en tipos de atributos |
| `ENTITY_RULE` | BR | Entity | Wiki-link a entidad en `## Declaración` de un BR |
| `ENTITY_POLICY` | BP | Entity | Wiki-link a entidad en `## Declaración` de un BP |
| `EMITS` | Entity/Command | Event | Wiki-links a `EVT-*` en secciones de postcondiciones o eventos |
| `CONSUMES` | Entity/Process | Event | Wiki-links a `EVT-*` en secciones de eventos consumidos |
| `UC_APPLIES_RULE` | UC | BR/BP/XP | Wiki-links en sección `## Reglas Aplicadas` |
| `UC_EXECUTES_CMD` | UC | CMD | Wiki-links en sección `## Comandos Ejecutados` |
| `UC_STORY` | UC | OBJ | Wiki-links a `OBJ-*` en contenido del UC |
| `VIEW_TRIGGERS_UC` | UI-View | UC | Wiki-links a `UC-*` en contenido de una vista |
| `VIEW_USES_COMPONENT` | UI-View | UI-Component | Wiki-links a componentes en contenido de una vista |
| `COMPONENT_USES_ENTITY` | UI-Component | Entity | Wiki-links a entidades en contenido de un componente |
| `REQ_TRACES_TO` | REQ | UC/BR/CMD | Wiki-links en sección `## Trazabilidad` |
| `VALIDATES` | BDD Feature | UC/BR/CMD | Tags o wiki-links en scenarios |
| `DECIDES_FOR` | ADR | Any | Wiki-links en contenido de un ADR |
| `CROSS_DOMAIN_REF` | Any | Any | Syntax `[[domain::Entity]]` en contenido |
| `LAYER_DEPENDENCY` | Node(layer N) | Node(layer M) | Implícita: N > M según 04→03→02→01 |

### Relaciones de negocio (minúsculas)

Las relaciones de negocio se definen libremente por los autores de specs, típicamente en la tabla `## Relaciones` de una entidad. Ejemplos: `aprueba`, `revisa`, `contiene`, `pertenece_a`, `paga`. El motor las extrae como edges con el nombre tal cual aparece en la tabla.

## Atributos

| Atributo | Tipo | Requerido | Descripción |
|----------|------|-----------|-------------|
| `from_node` | `string` | Sí | ID del nodo origen (e.g. `UC:UC-001`) |
| `to_node` | `string` | Sí | ID del nodo destino (e.g. `Entity:Pedido`) |
| `edge_type` | `string` | Sí | Tipo de relación. MAYÚSCULAS = estructural, minúsculas = negocio |
| `source_file` | `string` | Sí | Fichero del que se extrajo esta relación |
| `extraction_method` | `string` | Sí | Cómo se extrajo (`wiki_link`, `section_content`, `implicit`) |
| `metadata` | `dict` | No | Datos adicionales del edge (e.g. `cardinality`, `section_name`, `display_alias`) |
| `layer_violation` | `bool` | No | `true` si el edge viola la regla de dependencias de capa. Default `false` |
| `bidirectional` | `bool` | No | `true` para edges que se navegan en ambas direcciones (e.g. `WIKI_LINK`). Default `false` |

## Relaciones

| Relación | Cardinalidad | Destino | Descripción |
|----------|-------------|---------|-------------|
| desde | N:1 | [[GraphNode]] | Nodo origen del edge |
| hacia | N:1 | [[GraphNode]] | Nodo destino del edge |
| extraído de | N:1 | [[KDDDocument]] | Documento del que se extrajo |
| registrado en | N:1 | [[IndexManifest]] | Manifiesto que contiene este edge |

## Invariantes

- Un edge siempre conecta dos nodos existentes en el grafo. Si un nodo se elimina, todos sus edges asociados se eliminan en cascada.
- Los edge types estructurales (MAYÚSCULAS) deben ser uno de los tipos definidos en la tabla anterior. Los de negocio (minúsculas) son libres.
- Si `from_node.layer` < `to_node.layer` (e.g. `01-domain` → `02-behavior`), se establece `layer_violation: true` — excepto cuando el origen está en `00-requirements`, que está fuera del flujo de capas ([[BR-LAYER-001]]).
- No puede existir un edge duplicado con el mismo `from_node`, `to_node` y `edge_type`.
