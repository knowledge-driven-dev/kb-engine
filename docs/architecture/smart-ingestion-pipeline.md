# Pipeline de Indexación - Arquitectura

## Resumen

Este documento describe la arquitectura del pipeline de indexación implementado en `IndexationPipeline`. El pipeline es responsable de procesar documentos y almacenarlos en los tres repositorios del sistema (trazabilidad, vectorial y grafos).

---

## 1. Visión General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INDEXATION PIPELINE                                │
│                                                                         │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌─────────────────┐  │
│  │ Document  │──▶│ Frontmatter│──▶│ Chunking  │──▶│  Section Anchor │  │
│  │  Input    │   │ Extraction │   │ (per-type)│   │  Computation    │  │
│  └───────────┘   └───────────┘   └───────────┘   └─────────────────┘  │
│                                                          │              │
│                  ┌───────────────────────────────────────┘              │
│                  ▼                                                       │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐  │
│  │   Embedding     │──▶│   Entity        │──▶│  Storage Layer      │  │
│  │   Generation    │   │   Extraction    │   │                     │  │
│  │                 │   │   (optional)    │   │ ┌────────────────┐  │  │
│  └─────────────────┘   └─────────────────┘   │ │ Traceability   │  │  │
│                                               │ │ (SQLite/PG)    │  │  │
│                                               │ ├────────────────┤  │  │
│                                               │ │ Vector Store   │  │  │
│                                               │ │ (Chroma/Qdrant)│  │  │
│                                               │ ├────────────────┤  │  │
│                                               │ │ Graph Store    │  │  │
│                                               │ │ (SQLite/Neo4j) │  │  │
│                                               │ └────────────────┘  │  │
│                                               └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fases del Pipeline

### 2.1 Preparación del Documento

**Clase**: `IndexationPipeline._build_document()`

1. Lee el contenido del archivo
2. Determina el tipo de archivo por extensión → `FileTypeConfig`
3. Si es markdown, extrae frontmatter (YAML/TOML)
4. Construye el modelo `Document` con metadata, info git y parser asignado

**Formatos soportados** (configurables por `FileTypeConfig`):

| Extensión | Parser | MIME Type |
|-----------|--------|-----------|
| `.md` | markdown | text/markdown |
| `.json` | json | application/json |
| `.yaml`, `.yml` | yaml | text/yaml |
| `.rst` | rst | text/x-rst |
| Otros | plaintext | text/plain |

### 2.2 Chunking Semántico (ADR-0002)

**Clase**: `ChunkerFactory` → estrategias especializadas

El chunking usa estrategias específicas por tipo de documento KDD, seleccionadas según el campo `kind` del frontmatter:

| Estrategia | Tipo de Documento | ChunkType |
|------------|-------------------|-----------|
| `EntityChunkingStrategy` | entity | `ENTITY` |
| `UseCaseChunkingStrategy` | use_case | `USE_CASE` |
| `RuleChunkingStrategy` | rule | `RULE` |
| `ProcessChunkingStrategy` | process | `PROCESS` |
| `DefaultChunkingStrategy` | (fallback) | `DEFAULT` |

**Configuración** (`ChunkingConfig`):

```python
min_chunk_size: 100     # tokens mínimos
target_chunk_size: 512  # tokens objetivo
max_chunk_size: 1024    # tokens máximo
overlap_size: 50        # overlap entre chunks
preserve_sentences: True
respect_headings: True
include_heading_context: True
```

Cada chunk incluye:
- `heading_path`: Jerarquía de headings (ej: `["Documento", "Atributos"]`)
- `section_anchor`: Anchor URL calculado del heading path
- `chunk_type`: Tipo semántico del chunk

### 2.3 Generación de Embeddings

**Clase**: `EmbeddingProviderFactory` → `LocalEmbeddingProvider` | `OpenAIEmbeddingProvider`

| Proveedor | Modelo por defecto | Dimensiones |
|-----------|-------------------|-------------|
| `local` | all-MiniLM-L6-v2 (sentence-transformers) | 384 |
| `openai` | text-embedding-3-small | 1536 |

Los embeddings se generan por chunk y se almacenan en el Vector Store.

### 2.4 Extracción de Entidades (ADR-0003) — Opcional

**Clase**: `ExtractionPipelineFactory` → extractores

Solo se ejecuta si `graph_store != "none"`. Pipeline multi-estrategia:

1. **FrontmatterExtractor** — Extrae nodos del YAML frontmatter (confidence=1.0)
2. **PatternExtractor** — Detecta patrones en contenido (confidence=0.8-0.9):
   - Wiki links: `[[Entity]]`
   - IDs KDD: `UC-*`, `RUL-*`, `PRC-*`, `EVT-*`, etc.
   - Patrones de actores, sistemas, entidades en texto
3. **LLMExtractor** — Extracción semántica con OpenAI (confidence=0.7) — desactivado por defecto

**Deduplicación**: Por ID de nodo y por tupla (source, target, type) para edges.

### 2.5 Almacenamiento

El pipeline almacena en los tres repositorios de forma secuencial:

```
1. Document → Traceability Store
2. Chunks   → Traceability Store
3. Embeddings → Vector Store
4. Nodes/Edges → Graph Store (si disponible)
5. Status=INDEXED → Traceability Store (actualización)
```

Si cualquier paso falla, el documento se marca como `FAILED`.

---

## 3. Operaciones del Pipeline

### 3.1 Indexación de Documento Individual

```python
pipeline.index_document(document) → Document
```

Ejecuta el pipeline completo para un documento.

### 3.2 Indexación de Repositorio

```python
pipeline.index_repository(repo_config) → list[Document]
```

1. Escanea archivos del repo git que coincidan con patrones
2. Para cada archivo: construye `Document` → `index_document()`
3. Registra commit SHA y remote URL

### 3.3 Sincronización Incremental

```python
pipeline.sync_repository(repo_config, since_commit) → dict
```

1. Obtiene archivos cambiados y eliminados desde el commit dado
2. Elimina documentos de archivos borrados (cascade)
3. Reindexar archivos modificados (compara `content_hash` para saltar sin cambios)
4. Retorna: `{commit, indexed, deleted, skipped}`

### 3.4 Reindexación

```python
pipeline.reindex_document(document) → Document
```

Elimina datos derivados (vector, graph, chunks) y re-ejecuta `index_document()`.

### 3.5 Eliminación

```python
pipeline.delete_document(document) → bool
```

Eliminación en cascada: vector → graph → chunks → document.

---

## 4. Pipeline de Retrieval

**Clase**: `RetrievalPipeline`

Retorna `DocumentReference` con URLs en lugar de contenido raw:

```
Query (texto)
  ↓ [Embed query]
  ↓ [Vector search → chunk_ids + scores]
  ↓ [Fetch chunks + documents desde traceability]
  ↓ [Resolve URL: file:// o https://#anchor]
  ↓ [Return DocumentReferences]
RetrievalResponse
```

**Modos soportados**:
- `VECTOR`: Búsqueda por similitud de embeddings
- `GRAPH`: Traversal del grafo (placeholder)
- `HYBRID`: Combina ambos con Reciprocal Rank Fusion (RRF, k=60)

---

## 5. Diagrama de Secuencia

```
┌────────┐ ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐
│ Client │ │  Pipeline   │ │ Chunker  │ │ Embedding │ │ Extractor │ │  Stores  │
└───┬────┘ └──────┬──────┘ └────┬─────┘ └─────┬─────┘ └─────┬─────┘ └────┬─────┘
    │             │             │             │             │             │
    │ index_doc() │             │             │             │             │
    │────────────▶│             │             │             │             │
    │             │ save_doc    │             │             │             │
    │             │─────────────│─────────────│─────────────│────────────▶│
    │             │             │             │             │             │
    │             │ chunk()     │             │             │             │
    │             │────────────▶│             │             │             │
    │             │   chunks    │             │             │             │
    │             │◀────────────│             │             │             │
    │             │             │             │             │             │
    │             │ save_chunks │             │             │             │
    │             │─────────────│─────────────│─────────────│────────────▶│
    │             │             │             │             │             │
    │             │ embed_chunks│             │             │             │
    │             │─────────────│────────────▶│             │             │
    │             │  embeddings │             │             │             │
    │             │◀────────────│─────────────│             │             │
    │             │             │             │             │             │
    │             │ upsert_embeddings         │             │             │
    │             │─────────────│─────────────│─────────────│────────────▶│
    │             │             │             │             │             │
    │             │ extract_doc │             │             │             │
    │             │─────────────│─────────────│────────────▶│             │
    │             │   nodes     │             │             │             │
    │             │◀────────────│─────────────│─────────────│             │
    │             │             │             │             │             │
    │             │ create_nodes│             │             │             │
    │             │─────────────│─────────────│─────────────│────────────▶│
    │             │             │             │             │             │
    │  document   │             │             │             │             │
    │◀────────────│             │             │             │             │
```

---

## 6. Evolución Futura

Los siguientes Design Challenges pueden evolucionar este pipeline:

- **DC-002**: Estrategias de retrieval avanzadas (graph traversal, hybrid)
- **DC-009**: Actualización incremental a nivel de chunk (diff hash)
- **DC-011**: Ciclo de vida del contenido (dev → staging → pro → deprecated)

---

*Última actualización: Febrero 2026 (alineado con v0.2.0)*
