# Requisitos - Sistema RAG Híbrido

## 1. Contexto y Alcance

| Aspecto | Descripción |
|---------|-------------|
| **Dominio** | Desarrollo de código |
| **Fuentes** | Documentación (Markdown) + código fuente |
| **Consumidor** | Sistemas de desarrollo vía MCP (fuera de alcance inicial) |
| **Foco actual** | Backend |

## 2. Arquitectura General

### 2.1 Motores de Almacenamiento

| Motor | Propósito | Implementaciones |
|-------|-----------|------------------|
| **Trazabilidad** | Lineage, metadatos, relaciones documento→chunk→embedding→nodo | PostgreSQL |
| **Vectorial** | Búsqueda semántica (embeddings) | Qdrant, Weaviate, pgvector |
| **Grafos** | Modelo de conocimiento multicapa (entidades KDD) | Neo4j, NebulaGraph |

> **Decisión**: Se mantienen las 3 BBDD separadas para no limitar la elección de motor vectorial o de grafos.

### 2.2 Separación de Procesos

El sistema separa dos procesos principales que comparten las bases de datos:

- **Indexación**: Ingesta, procesamiento y almacenamiento de conocimiento
- **Inferencia**: Consulta y recuperación de información

### 2.3 Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python |
| **Framework RAG** | LlamaIndex |
| **Cloud** | Agnóstico |

El diseño debe ser agnóstico en bases de datos, con abstracciones sobre implementaciones concretas:

**Bases de datos de grafos soportadas:**
- Neo4j
- NebulaGraph

**Bases de datos vectoriales soportadas:**
- Qdrant
- Weaviate
- pgvector

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

### 3.3 Tipos de Nodos (Fase 1 - Capa Funcional)

Basados en la metodología KDD:

| Categoría | Tipo de Nodo | Descripción |
|-----------|--------------|-------------|
| **Visión** | `PRD` | Product Requirement Document por epic |
| **Dominio** | `Entity` | Entidades y value objects del dominio |
| **Dominio** | `Event` | Eventos de dominio (EVT-*) |
| **Dominio** | `Rule` | Reglas de negocio (RUL-*) |
| **Comportamiento** | `UseCase` | Casos de uso (UC-*) |
| **Comportamiento** | `Process` | Procesos/flujos (PRC-*) |
| **Comportamiento** | `Story` | Historias de usuario |
| **Comportamiento** | `Requirement` | Requisitos funcionales (REQ-*) |
| **Interfaces** | `API` | Contratos OpenAPI |
| **Interfaces** | `AsyncAPI` | Contratos de eventos async |
| **Interfaces** | `UIContract` | Contratos de UI |
| **Calidad** | `NFR` | Requisitos no funcionales |
| **Calidad** | `ADR` | Decisiones arquitectónicas |
| **Calidad** | `Scenario` | Escenarios SBE (I/O) |
| **Calidad** | `Gherkin` | Features/scenarios ejecutables |

### 3.4 Tipos de Relaciones

| Relación | Origen | Destino | Descripción |
|----------|--------|---------|-------------|
| `RELATES_TO` | PRD | UseCase, NFR, API | PRD referencia artefactos |
| `INVOKES` | UseCase | Rule | Caso de uso invoca reglas |
| `PRODUCES` | UseCase | Event | Caso de uso produce eventos |
| `RELATES_TO` | UseCase | Story | UC relacionado con historias |
| `EMITS` | Entity | Event | Entidad emite eventos |
| `CONSUMES` | Entity | Event | Entidad consume eventos |
| `HAS_STATE` | Entity | StateMachine | Entidad tiene ciclo de vida |
| `VALIDATES` | Scenario | UseCase, Rule | Escenario valida UC/regla |
| `BELONGS_TO` | * | Domain | Pertenencia a dominio/proyecto |
| `DEPENDS_ON` | * | * | Dependencia genérica |

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

### 4.2 Ciclo de Vida del Contenido

El contenido indexado tiene un ciclo de vida que refleja el estado del desarrollo:

| Estado | Descripción |
|--------|-------------|
| `dev` | En desarrollo - funcionalidad definida pero no desplegada |
| `staging` | Pendiente de despliegue |
| `pro` | En producción - desplegado y verificable |
| `deprecated` | Obsoleto - marcado para eliminación |

**Características:**
- El estado se asigna al **documento** en momento de indexación
- El estado se **propaga** a todos los elementos derivados (chunks, embeddings, nodos)
- Las **queries de inferencia** filtran por estado según el contexto
- Cambio de estado se propaga sin reindexación

**Ejemplo de uso:**
```
1. Indexar requisito nuevo → state: dev
2. Todos los derivados heredan state: dev
3. Query en contexto desarrollo → incluye dev + pro
4. Query en contexto producción → solo pro
5. Despliegue → cambiar state a pro → propagar
```

### 4.3 Entidades de Trazabilidad

```
┌──────────────────┐
│     Document     │
│──────────────────│
│ id (uuid)        │
│ external_ref     │  ← ruta en repo (ej: /specs/domain/entities/User.md)
│ source_type      │  ← 'repository' | 'upload'
│ kind             │  ← tipo KDD (entity, rule, use_case...)
│ domain           │  ← proyecto/dominio
│ lifecycle_state  │  ← dev | staging | pro | deprecated
│ status           │
│ hash             │  ← para detectar cambios en contenido
│ ──── Git ─────── │
│ git_repo         │  ← URL o identificador del repositorio
│ git_ref          │  ← ref indexada (branch, tag, commit)
│ git_commit_sha   │  ← SHA del commit exacto indexado
│ git_ref_type     │  ← 'branch' | 'tag' | 'commit'
│ ──── Timestamps ─│
│ indexed_at       │  ← cuándo se indexó esta versión
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
│ sequence         │  ← orden dentro del documento
│ content          │
│ metadata (jsonb) │  ← info específica del chunk
│ lifecycle_state  │  ← heredado del documento
│ hash             │
└────────┬─────────┘
         │ 1:1
         ▼
┌──────────────────┐
│    Embedding     │
│──────────────────│
│ id (uuid)        │
│ chunk_id (fk)    │
│ vector_db_ref    │  ← ID en la BBDD vectorial
│ model            │  ← modelo usado para embedding
│ lifecycle_state  │  ← heredado del chunk
│ created_at       │
└──────────────────┘

┌──────────────────┐
│   GraphNode      │
│──────────────────│
│ id (uuid)        │
│ document_id (fk) │  ← documento origen
│ chunk_id (fk)    │  ← chunk origen (opcional)
│ graph_db_ref     │  ← ID en la BBDD de grafos
│ node_type        │  ← tipo de nodo KDD
│ lifecycle_state  │  ← heredado del documento
│ status           │  ← draft | validated | approved
│ created_at       │
└──────────────────┘

┌──────────────────┐
│   GraphEdge      │
│──────────────────│
│ id (uuid)        │
│ document_id (fk) │  ← documento origen
│ graph_db_ref     │  ← ID en la BBDD de grafos
│ edge_type        │  ← tipo de relación
│ source_node_id   │
│ target_node_id   │
│ lifecycle_state  │  ← heredado del documento
│ status           │
│ created_at       │
└──────────────────┘
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

### 5.4 Extracción de Entidades

El pipeline incluye un paso de extracción de entidades y relaciones:

- **Estrategias configurables**:
  - Modelos eficientes (spaCy)
  - Modelos avanzados (LLM externos)
- **Validación humana**: Requerida para curación
- **Futuro rol**: Knowledge Manager / Knowledge Owner

## 6. Pipeline de Inferencia (Retrieval)

### 6.1 Estrategia Híbrida Principal

```
Grafo (expansión de contexto) → Vector (búsqueda semántica)
```

### 6.2 Algoritmos de Recuperación

- **Estrategia por defecto**: Inspirada en papers de referencia
- Múltiples estrategias disponibles y configurables
- **Selección automática**: Algoritmo (LLM pequeño) detecta tipo de conversación y selecciona estrategia óptima
- Tipos por definir:
  - [ ] Solo vector (semántico puro)
  - [ ] Solo grafo (traversal)
  - [ ] Híbrido (grafo + vector)
  - [ ] Keyword/BM25
  - [ ] Otros

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

- [x] ~~Tipos de nodos y relaciones del grafo~~ (basado en KDD)
- [x] ~~Tipos específicos de documentos y sus pipelines~~ (basado en KDD)
- [x] ~~Ciclo de vida del contenido~~ (dev, staging, pro, deprecated)
- [ ] Modelo de API del backend
- [ ] Papers de referencia para estrategia de retrieval por defecto
- [ ] Detalle de algoritmos de retrieval a implementar
- [ ] Diseño de UI de curación
- [ ] Modelo de integración con IdP

---

*Documento en evolución - Última actualización: Sesión de requisitos inicial*
