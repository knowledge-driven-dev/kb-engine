---
kind: entity
aliases: [Vector, EmbeddingVector, Chunk]
status: draft
---

# Embedding

## Descripción

Un [[Embedding]] es un vector semántico generado a partir de un **fragmento** (párrafo o atributo) de un [[KDDDocument]] original. El [[Embedding]] y el [[GraphNode]] son productos hermanos de la indexación: ambos se originan del mismo documento, pero el nodo captura la estructura extraída mientras que el embedding captura la semántica del texto original.

No todos los documentos ni todas las secciones reciben embeddings: la regla [[BR-EMBEDDING-001]] define qué secciones de cada `kind` se embeben. Dentro de esas secciones, se aplica un **chunking jerárquico por párrafos**: cada párrafo o atributo individual produce un embedding, y el texto que se embebe se enriquece con un resumen de las secciones padre para preservar el contexto jerárquico del documento.

### Contexto jerárquico

En lugar de usar overlapping entre chunks, cada fragmento se embebe con una "línea de contexto" compuesta por resúmenes de sus secciones ancestro. Ejemplo para un párrafo dentro de `## Flujo Principal > ### Paso 3`:

```
[KDDDocument: UC-001-IndexDocument | Use Case] >
[Flujo Principal: resumen del flujo completo] >
[Paso 3: El sistema extrae los wiki-links del contenido y genera edges...]
```

Esto permite que la búsqueda semántica encuentre fragmentos específicos sin perder el contexto de dónde viven dentro del documento.

Los embeddings se generan en el nivel L2 (Semántico) del pipeline de indexación, usando un modelo local portable como `nomic-embed-text` o `bge-small-en-v1.5`. Se almacenan como archivos binarios en `.kdd-index/embeddings/` y se usan para búsqueda semántica y para el componente semántico de la búsqueda híbrida.

## Atributos

| Atributo | Tipo | Requerido | Descripción |
|----------|------|-----------|-------------|
| `id` | `string` | Sí | Identificador compuesto `{document_id}:{section_path}:{chunk_index}` (e.g. `UC-001:flujo_principal:3`) |
| `document_id` | `string` | Sí | ID del [[KDDDocument]] de origen |
| `document_kind` | `KDDKind` | Sí | `kind` del documento de origen (para filtrado eficiente) |
| `section_path` | `string` | Sí | Ruta jerárquica de la sección dentro del documento (e.g. `descripcion`, `flujo_principal.paso_3`) |
| `chunk_index` | `int` | Sí | Índice del chunk dentro de la sección (0-based). Normalmente un párrafo = un chunk |
| `raw_text` | `string` | Sí | Texto original del párrafo/atributo tal como aparece en el documento |
| `context_text` | `string` | Sí | Texto enriquecido con resúmenes de secciones padre (es lo que realmente se embebe) |
| `vector` | `float[]` | Sí | Vector de embeddings (dimensión según modelo, e.g. 768 para nomic-embed-text) |
| `model` | `string` | Sí | Identificador del modelo usado (e.g. `nomic-embed-text-v1.5`) |
| `dimensions` | `int` | Sí | Número de dimensiones del vector |
| `text_hash` | `string` | Sí | Hash de `context_text` para detectar si necesita regenerarse |
| `generated_at` | `datetime` | Sí | Timestamp de generación |

## Relaciones

| Relación | Cardinalidad | Destino | Descripción |
|----------|-------------|---------|-------------|
| originado por | N:1 | [[KDDDocument]] | El documento fuente del que se extrajo el fragmento |
| registrado en | N:1 | [[IndexManifest]] | Manifiesto que registra el modelo y dimensiones |

## Invariantes

- La `section_path` debe pertenecer a una de las secciones embebibles para el `document_kind`, según [[BR-EMBEDDING-001]].
- El `model` y `dimensions` deben coincidir con los declarados en el [[IndexManifest]] del índice.
- El `context_text` siempre incluye al menos el `raw_text`. Si el párrafo está en una sección raíz, `context_text` = resumen del documento + `raw_text`.
- Si el `text_hash` del embedding difiere del hash actual del `context_text` recalculado, el embedding está desactualizado y debe regenerarse.
- Dos embeddings del mismo índice nunca pueden tener el mismo `id`.
- Al eliminar un [[KDDDocument]], todos sus embeddings asociados se eliminan en cascada.
