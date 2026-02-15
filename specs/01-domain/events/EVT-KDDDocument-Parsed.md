---
id: EVT-KDDDocument-Parsed
kind: event
title: "KDDDocument Parsed"
status: draft
---

# EVT-KDDDocument-Parsed

## Descripción

Se emite cuando un [[KDDDocument]] ha sido parseado exitosamente por el extractor correspondiente a su `kind`. En este punto, el front-matter, las secciones Markdown y los wiki-links han sido extraídos del texto original, pero aún no se ha generado el [[GraphNode]] ni los [[Embedding|embeddings]].

Este evento marca la transición `detected → parsing` o `stale → parsing` en el ciclo de vida del documento. Es un evento interno del pipeline que indica que la fase de lectura y parsing ha completado sin errores.

## Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | `string` | ID del documento parseado |
| `source_path` | `string` | Ruta relativa del fichero |
| `kind` | `KDDKind` | Tipo de artefacto KDD |
| `front_matter` | `dict` | Front-matter YAML extraído |
| `section_count` | `int` | Número de secciones Markdown encontradas |
| `wiki_link_count` | `int` | Número de wiki-links `[[...]]` encontrados |
| `parsed_at` | `datetime` | Timestamp del parsing |

## Productor

- Extractor de documentos KDD (uno por `kind`)

## Consumidores

- Generador de nodos: crea el [[GraphNode]] a partir de los campos extraídos
- Generador de edges: crea [[GraphEdge|edges]] a partir de wiki-links, front-matter y secciones
- Generador de embeddings: aplica chunking jerárquico a las secciones embebibles según [[BR-EMBEDDING-001]]
