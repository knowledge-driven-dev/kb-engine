# Requisitos - Sistema de Retrieval de Conocimiento

## 1. Contexto y Alcance

| Aspecto | Descripción |
|---------|-------------|
| **Dominio** | Desarrollo de código |
| **Fuentes** | Documentación (Markdown, JSON, YAML, RST) + código fuente |
| **Consumidor** | Sistemas de desarrollo vía MCP (fuera de alcance inicial) |
| **Foco actual** | Backend |

## 2. Arquitectura General

### 2.1 Motores de Almacenamiento

| Motor | Propósito | Perfil Local | Perfil Server |
|-------|-----------|--------------|---------------|
| **Trazabilidad** | Lineage, metadatos, relaciones documento→chunk→embedding→nodo | SQLite | PostgreSQL |
| **Vectorial** | Búsqueda semántica (embeddings) | ChromaDB | Qdrant |
| **Grafos** | Modelo de conocimiento (entidades KDD) — opcional | SQLite | Neo4j |

> **Decisión**: Se mantienen las 3 BBDD separadas (ver ADR-0001). El almacenamiento de grafos puede desactivarse con `graph_store="none"`.

### 2.2 Separación de Procesos

El sistema separa dos procesos principales que comparten las bases de datos:

- **Indexación**: Ingesta, procesamiento y almacenamiento de conocimiento
- **Retrieval**: Búsqueda y recuperación de referencias a documentos

### 2.3 Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.11+ |
| **Framework API** | FastAPI |
| **Abstracciones** | Repository Pattern con Factory (ADR-0001) |
| **Cloud** | Agnóstico |

### 2.4 Perfiles de Configuración

| Perfil | Trazabilidad | Vectorial | Grafos | Embeddings |
|--------|-------------|-----------|--------|------------|
| **local** (desarrollo) | SQLite | ChromaDB | SQLite | sentence-transformers (all-MiniLM-L6-v2) |
| **server** (producción) | PostgreSQL | Qdrant | Neo4j | OpenAI (text-embedding-3-small) |

El diseño es agnóstico en bases de datos gracias al Repository Pattern, con abstracciones sobre implementaciones concretas.

## 3. Modelo de Grafos

### 3.1 Capas (Desarrollo Incremental)

| Fase | Capa | Contenido |
|------|------|-----------|
| 1 (actual) | Funcional | Entidades KDD: PRD, Entity, Rule, UseCase, Process, Event, etc. |
| 2 (futuro) | Física | Tablas, servicios, pantallas |

### 3.2 Características

- **Granularidad**: Alta (mucho detalle)
- **Origen de entidades**: Extraídas de documentación KDD
- **Metodología base**: Knowledge-Driven Development (KDD) - ver `docs/design/kdd.md`

### 3.3 Tipos de Nodos (Implementados)

Definidos en `kb_engine.core.models.graph.NodeType`:

| Categoría | Tipo de Nodo | Descripción |
|-----------|--------------|-------------|
| **Dominio** | `ENTITY` | Entidades y value objects del dominio |
| **Dominio** | `RULE` | Reglas de negocio |
| **Comportamiento** | `USE_CASE` | Casos de uso |
| **Comportamiento** | `PROCESS` | Procesos/flujos |
| **Actores** | `ACTOR` | Actores del sistema (usuarios, roles) |
| **Actores** | `SYSTEM` | Sistemas o servicios |
| **General** | `CONCEPT` | Conceptos genéricos |
| **Estructural** | `DOCUMENT` | Referencia a documento fuente |
| **Estructural** | `CHUNK` | Referencia a chunk fuente |

### 3.4 Tipos de Relaciones

Definidos en `kb_engine.core.models.graph.EdgeType`:

| Relación | Categoría | Descripción |
|----------|-----------|-------------|
| `CONTAINS` | Estructural | Contención jerárquica |
| `PART_OF` | Estructural | Pertenencia |
| `REFERENCES` | Estructural | Referencia genérica |
| `IMPLEMENTS` | Dominio | Implementación |
| `DEPENDS_ON` | Dominio | Dependencia |
| `RELATED_TO` | Dominio | Relación genérica |
| `TRIGGERS` | Dominio | Disparo de acción |
| `USES` | Dominio | Uso/consumo |
| `PRODUCES` | Dominio | Producción |
| `PERFORMS` | Actor | Actor ejecuta acción |
| `OWNS` | Actor | Propiedad |
| `SIMILAR_TO` | Semántico | Similitud semántica |
| `CONTRADICTS` | Semántico | Contradicción |
| `EXTENDS` | Semántico | Extensión |

### 3.5 Propiedades Comunes de Nodos

Basadas en el front-matter KDD:

```yaml
id: string          # Identificador único (ej: UC-Checkout@v1)
kind: string        # Tipo de artefacto
status: enum        # draft | proposed | approved | deprecated
aliases: string[]   # Nombres alternativos
tags: string[]      # Etiquetas para clasificación
domain: string      # Dominio/proyecto al que pertenece
source_file: string # Archivo origen en el repositorio
```

## 4. Modelo de Trazabilidad

### 4.1 Propósito

Trazabilidad total entre todas las piezas del sistema para:
- Saber todo lo inferido a partir de un documento (nodos, relaciones, embeddings)
- Actualización precisa a nivel de chunk cuando cambia un documento
- Reindexación selectiva o completa de documentos
- Borrado en cascada cuando se elimina un documento

### 4.2 Estado de Procesamiento de Documentos

Los documentos tienen un estado de procesamiento (`DocumentStatus`):

| Estado | Descripción |
|--------|-------------|
| `PENDING` | Documento registrado, pendiente de procesamiento |
| `PROCESSING` | Pipeline de indexación en curso |
| `INDEXED` | Indexación completada exitosamente |
| `FAILED` | Error durante indexación |
| `ARCHIVED` | Archivado / fuera de uso |

> **Nota**: El ciclo de vida del contenido (dev → staging → pro → deprecated) está pendiente de implementación (ver DC-011). Actualmente el sistema gestiona solo el estado de procesamiento.

### 4.3 Entidades de Trazabilidad (Implementadas)

Basadas en los modelos Pydantic en `kb_engine.core.models`:

```
┌──────────────────┐
│     Document     │
│──────────────────│
│ id (uuid)        │
│ external_id      │  ← repo_name:relative_path
│ title            │
│ content          │
│ source_path      │
│ mime_type         │  ← text/markdown, application/json, etc.
│ domain           │  ← proyecto/dominio
│ tags             │  ← etiquetas del frontmatter
│ metadata (dict)  │  ← info del frontmatter + _parser
│ status           │  ← PENDING | PROCESSING | INDEXED | FAILED | ARCHIVED
│ content_hash     │  ← SHA256 para detectar cambios
│ ──── Git ─────── │
│ repo_name        │  ← nombre del repositorio
│ relative_path    │  ← ruta relativa en el repo
│ git_commit       │  ← SHA del commit indexado
│ git_remote_url   │  ← URL del remote
│ ──── Timestamps ─│
│ created_at       │
│ updated_at       │
└────────┬─────────┘
         │ 1:N
         ▼
┌──────────────────┐
│      Chunk       │
│──────────────────│
│ id (uuid)        │
│ document_id (fk) │
│ content          │
│ chunk_type       │  ← ENTITY | USE_CASE | RULE | PROCESS | DEFAULT
│ heading_path     │  ← jerarquía de headings [H1, H2, H3]
│ section_anchor   │  ← anchor calculado del heading_path
│ start_offset     │
│ end_offset       │
│ metadata (dict)  │
│ content_hash     │
└────────┬─────────┘
         │ 1:1
         ▼
┌──────────────────┐
│    Embedding     │
│──────────────────│
│ id (uuid)        │
│ chunk_id (fk)    │
│ vector           │  ← list[float]
│ model            │  ← modelo usado (all-MiniLM-L6-v2 o text-embedding-3-small)
│ dimensions       │
│ metadata (dict)  │
└──────────────────┘

┌──────────────────┐      ┌──────────────────┐
│      Node        │      │      Edge        │
│──────────────────│      │──────────────────│
│ id (uuid)        │      │ id (uuid)        │
│ external_id      │      │ source_id (fk)   │
│ name             │      │ target_id (fk)   │
│ node_type        │      │ edge_type        │
│ description      │      │ name             │
│ source_doc_id    │      │ properties       │
│ source_chunk_id  │      │ weight           │
│ properties       │      │ source_doc_id    │
│ confidence       │      │ source_chunk_id  │
│ extraction_method│      │ confidence       │
│ created_at       │      │ extraction_method│
│ updated_at       │      │ created_at       │
└──────────────────┘      └──────────────────┘
```

### 4.4 Operaciones de Trazabilidad

| Operación | Descripción |
|-----------|-------------|
| **Crear documento** | Inserta Document + genera Chunks + Embeddings + Nodos/Edges |
| **Actualizar documento** | Compara hash, actualiza solo chunks modificados, propaga cambios |
| **Eliminar documento** | Borra en cascada: Document → Chunks → Embeddings → Nodos → Edges |
| **Consultar lineage** | Dado un documento, obtener todos sus derivados |
| **Consultar origen** | Dado un nodo/embedding, obtener documento y chunk origen |

## 5. Pipeline de Indexación

### 5.1 Características Generales

- Pipelines específicos por tipo de documento KDD
- Configurables por código (Python)
- Chunking preciso (estructura KDD conocida)

### 5.2 Tipos de Documentos y Pipelines

Basados en la estructura KDD:

| Fuente | Tipo de Documento | Pipeline |
|--------|-------------------|----------|
| `/specs/vision/` | PRD | Pipeline PRD |
| `/specs/domain/entities/` | Entity | Pipeline Entity |
| `/specs/domain/events/` | Event | Pipeline Event |
| `/specs/domain/rules/` | Rule | Pipeline Rule |
| `/specs/behavior/use-cases/` | UseCase | Pipeline UseCase |
| `/specs/behavior/processes/` | Process | Pipeline Process |
| `/specs/behavior/stories/` | Story | Pipeline Story |
| `/specs/interfaces/api/` | OpenAPI | Pipeline API |
| `/specs/interfaces/async/` | AsyncAPI | Pipeline AsyncAPI |
| `/specs/examples/` | Scenario, Gherkin | Pipeline SBE |
| `/specs/quality/` | NFR | Pipeline NFR |
| `/specs/architecture/adr/` | ADR | Pipeline ADR |

### 5.3 Pasos del Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Ingesta   │───▶│   Parsing   │───▶│  Chunking   │───▶│  Embedding  │
│  (fuentes)  │    │ (front-matter│    │ (específico │    │ (vectores)  │
└─────────────┘    │  + contenido)│    │  por tipo)  │    └─────────────┘
                   └─────────────┘    └─────────────┘           │
                                                                 ▼
                                                          ┌─────────────┐
                                                          │   Vector    │
                                                          │     DB      │
                                                          └─────────────┘
                          │
                          ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │ Extracción  │───▶│ Validación  │───▶│   Graph     │
                   │ Entidades   │    │  (humana)   │    │     DB      │
                   │ + Relaciones│    │             │    │             │
                   └─────────────┘    └─────────────┘    └─────────────┘
```

### 5.4 Extracción de Entidades (ADR-0003)

Pipeline multi-estrategia implementado en `kb_engine.extraction`:

- **FrontmatterExtractor**: Extrae del YAML frontmatter (confidence=1.0)
- **PatternExtractor**: Detecta patrones en contenido: wiki links `[[Entity]]`, IDs KDD `UC-*`, `RUL-*` (confidence=0.8-0.9)
- **LLMExtractor**: Extracción semántica con OpenAI (confidence=0.7) — **opcional**, desactivado por defecto
- **Deduplicación** automática por ID y (source, target, type)
- El grafo es **opcional**: si `graph_store="none"`, la extracción se omite

## 6. Pipeline de Retrieval

### 6.1 Arquitectura

El `RetrievalPipeline` retorna `DocumentReference` con URLs (file:// o https://#anchor) en lugar de contenido raw. Esto permite a agentes externos leer los documentos fuente directamente.

### 6.2 Modos de Retrieval (Implementados)

| Modo | Descripción | Estado |
|------|-------------|--------|
| `VECTOR` | Búsqueda semántica por similitud de embeddings | Implementado |
| `GRAPH` | Búsqueda por traversal del grafo | Placeholder |
| `HYBRID` | Combina vector + graph con Reciprocal Rank Fusion | Implementado (merge) |

### 6.3 Requisitos de Rendimiento

- **Latencia**: Muy baja (prioridad)

## 7. Seguridad (By Design)

### 7.1 RBAC

| Aspecto | Detalle |
|---------|---------|
| **Nivel de control** | Documento + Proyecto/Dominio |
| **Origen de roles** | Externo (IdP) |
| **Aplicación** | Sobre grafo Y vector |

### 7.2 Multi-tenancy

- Un despliegue por dominio/proyecto
- No se comparte entre clientes (aislamiento total)

## 8. Interfaces

### 8.1 UI de Curación

- Interfaz propia para validación humana
- Gestión de entidades y grafos
- Herramientas para Knowledge Manager (futuro)

### 8.2 API

Por definir

## 9. Volumetría

| Métrica | Valor |
|---------|-------|
| Documentos por aplicación | ~1500 (escalable a aplicaciones grandes) |

## 10. Requisitos Pendientes de Definir

- [x] ~~Tipos de nodos y relaciones del grafo~~ (implementados en `graph.py`)
- [x] ~~Tipos específicos de documentos y sus pipelines~~ (basado en KDD)
- [x] ~~Repository Pattern para abstracción de almacenamiento~~ (ADR-0001)
- [x] ~~Estrategia de chunking semántico~~ (ADR-0002)
- [x] ~~Pipeline de extracción multi-estrategia~~ (ADR-0003)
- [ ] Ciclo de vida del contenido (DC-011)
- [ ] Modelo de API del backend (DC-006)
- [ ] Papers de referencia para estrategia de retrieval por defecto (DC-002)
- [ ] Diseño de UI de curación (DC-007)
- [ ] Modelo de integración con IdP (DC-005)

---

*Documento en evolución - Última actualización: Febrero 2026 (alineado con v0.2.0)*
