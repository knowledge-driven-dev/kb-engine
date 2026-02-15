---
id: CMD-001
kind: command
title: IndexDocument
status: draft
---

# CMD-001 — IndexDocument

## Purpose

Indexar un [[KDDDocument]] individual, ejecutando el pipeline completo: detección de `kind` ([[BR-DOCUMENT-001]]), extracción de [[GraphNode]] y [[GraphEdge|edges]], generación de [[Embedding|embeddings]] (si nivel ≥ L2 según [[BR-INDEX-001]]), y almacenamiento en `.kdd-index/`.

Este comando es la unidad atómica de indexación. Tanto la indexación completa como la incremental ([[CMD-002-IndexIncremental]]) invocan este comando para cada documento individual.

## Input

| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|
| `source_path` | `string` | Sí | Debe ser una ruta válida dentro de `/specs`. El fichero debe existir y contener front-matter con `kind` reconocido |
| `index_path` | `string` | No | Ruta a `.kdd-index/`. Default: `.kdd-index/` en la raíz del repositorio |
| `force` | `bool` | No | Si `true`, re-indexa aunque el `source_hash` no haya cambiado. Default `false` |

## Preconditions

- El fichero en `source_path` existe y es legible.
- El directorio `index_path` existe o puede crearse.
- El nivel de indexación ha sido determinado ([[BR-INDEX-001]]).

## Postconditions

- Se emite [[EVT-KDDDocument-Detected]] al inicio.
- Se emite [[EVT-KDDDocument-Parsed]] tras el parsing exitoso.
- Un [[GraphNode]] con id `{Kind}:{DocumentId}` ha sido creado o actualizado en `.kdd-index/nodes/`.
- Los [[GraphEdge|edges]] extraídos del documento se han escrito en `.kdd-index/edges/edges.jsonl`.
- Si nivel ≥ L2: los [[Embedding|embeddings]] de las secciones embebibles ([[BR-EMBEDDING-001]]) se han generado y almacenado en `.kdd-index/embeddings/`.
- La validación de capas ([[BR-LAYER-001]]) se ha ejecutado sobre todos los edges generados.
- Se emite [[EVT-KDDDocument-Indexed]] con métricas de duración.
- El [[IndexManifest]] se ha actualizado con las estadísticas incrementadas.

## Possible Errors

| Code | Condition | Message |
|------|-----------|---------|
| `DOCUMENT_NOT_FOUND` | El fichero en `source_path` no existe | "Document not found: {source_path}" |
| `INVALID_FRONT_MATTER` | El fichero no tiene front-matter YAML válido | "Invalid or missing front-matter in {source_path}" |
| `UNKNOWN_KIND` | El `kind` del front-matter no es reconocido por [[BR-DOCUMENT-001]] | "Unknown kind '{kind}' in {source_path}" |
| `EXTRACTION_FAILED` | El extractor falló al parsear el contenido | "Extraction failed for {source_path}: {detail}" |
| `EMBEDDING_FAILED` | El modelo de embeddings falló (degradación a L1) | "Embedding generation failed, falling back to L1: {detail}" |
| `INDEX_WRITE_FAILED` | No se puede escribir en `index_path` | "Cannot write to index path: {index_path}" |
