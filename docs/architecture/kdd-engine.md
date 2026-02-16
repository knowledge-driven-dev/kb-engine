# KDD Engine (v2)

Motor de retrieval para especificaciones KDD. Indexa artefactos de dominio (entidades, eventos, reglas, comandos, queries, casos de uso) y ofrece busqueda hibrida (semantica + grafo + lexical) para agentes de IA.

> **Paquete**: `src/kdd/` | **CLI**: `kdd` | **Entrada**: `kdd.api.cli:cli`

---

## Arquitectura

Hexagonal (Ports & Adapters) con CQRS (Commands/Queries separados):

```
src/kdd/
├── domain/              # Entidades, enums, reglas puras, ports (Protocol)
├── application/         # Commands (write) + Queries (read) + Extractors
├── infrastructure/      # Adapters: filesystem, networkx, hnswlib, git, events
├── api/                 # Entry points: CLI (Click) + Server (FastAPI)
└── container.py         # DI container — ensambla todo
```

### Flujo de dependencias

```
api/ ──▶ application/ ──▶ domain/
              │
              ▼
        infrastructure/   (implementa domain/ports.py)
```

El dominio no importa nada de infrastructure. Los adapters implementan los `Protocol` definidos en `domain/ports.py`.

### Ports (interfaces)

| Port | Responsabilidad | Adapter por defecto |
|------|----------------|---------------------|
| `ArtifactStore` | Leer/escribir `.kdd-index/` | `FilesystemArtifactStore` |
| `GraphStore` | Grafo en memoria para queries | `NetworkXGraphStore` |
| `VectorStore` | Indice vectorial para semantic search | `HNSWLibVectorStore` |
| `EmbeddingModel` | Generar embeddings desde texto | `SentenceTransformerModel` |
| `EventBus` | Pub/sub de domain events | `InMemoryEventBus` |
| `AgentClient` | Enrichment L3 via agente IA | (pendiente) |
| `Transport` | Push/pull de artifacts a remoto | (pendiente) |

---

## Index Levels (Capacidad Progresiva)

El engine detecta automaticamente el nivel disponible segun las dependencias instaladas:

```
L1 ─────────────────────────────────────────────────────── Siempre disponible
  Grafo de nodos/edges extraidos de front-matter + wiki-links
  NetworkX en memoria, sin embeddings
  Busqueda: grafo + lexical

L2 ─────────────────────────────────────── sentence-transformers + hnswlib
  Todo L1 + embeddings vectoriales (384 dims, all-MiniLM-L6-v2)
  HNSWLib en memoria
  Busqueda: hibrida (semantica + grafo + lexical)

L3 ──────────────────────────────────────────────── API de agente IA (TBD)
  Todo L2 + enrichment con agente
  Analisis de impacto semantico
```

**Instalacion por nivel:**

```bash
pip install -e ".[kdd]"          # L1
pip install -e ".[kdd,kdd-l2]"   # L2
```

---

## Artifact Store (`.kdd-index/`)

El indice se persiste como ficheros JSON en disco. No requiere base de datos:

```
.kdd-index/
├── manifest.json          # IndexManifest: version, stats, git_commit, level
├── nodes/
│   ├── entity/
│   │   ├── User.json      # GraphNode serializado
│   │   └── Order.json
│   ├── command/
│   │   └── CMD-001.json
│   └── ...                # Un directorio por KDDKind
├── edges/
│   └── edges.jsonl        # GraphEdge stream (append-only JSONL)
└── embeddings/
    ├── entity/
    │   └── User.json      # Lista de Embedding objects
    └── ...
```

Al arrancar un query, el `IndexLoader` lee los artifacts de disco y los carga en los stores en memoria (NetworkX + HNSWLib).

---

## CQRS: Commands

### CMD-001 — IndexDocument

Procesa un unico fichero de spec:

1. Lee fichero, extrae front-matter
2. Routea documento via `BR-DOCUMENT-001` (kind + validacion de ubicacion)
3. Extrae `GraphNode` + `GraphEdge[]` con extractor especifico del kind
4. Valida dependencias de capa (`BR-LAYER-001`)
5. (L2+) Chunking semantico + embeddings (`BR-EMBEDDING-001`)
6. Escribe artifacts en `ArtifactStore`
7. Emite domain events (`DocumentDetected` → `DocumentParsed` → `DocumentIndexed`)

### CMD-002 — IndexIncremental

Usa `git diff` para indexar solo cambios:

- **Sin manifest previo** → full reindex de todos los `**/*.md`
- **Con manifest** → diff contra `git_commit` del manifest:
  - Ficheros nuevos → index via CMD-001
  - Ficheros modificados → delete artifacts + re-index
  - Ficheros eliminados → cascade delete artifacts

### CMD-004 — MergeIndex

Combina multiples `.kdd-index/` de diferentes desarrolladores:

- Estrategia de conflictos: `last_write_wins` (por defecto) o `fail_on_conflict`
- Resolucion: el nodo con `indexed_at` mas reciente gana (`BR-MERGE-001`)
- Delete-wins: si un nodo esta ausente en cualquier indice, se elimina

### CMD-005 — SyncIndex (pendiente)

Push/pull de `.kdd-index/` a remoto via `Transport` port.

---

## CQRS: Queries

### QRY-003 — RetrieveHybrid (query principal)

Busqueda hibrida con fusion de scores. Es el query por defecto para agentes.

**Fases:**
1. **Semantic** (L2+): encode query → busqueda vectorial en HNSWLib
2. **Lexical**: text search sobre campos indexados en GraphStore
3. **Graph expansion**: BFS desde nodos encontrados, profundidad configurable
4. **Fusion scoring**: ponderacion `semantic(0.6) + graph(0.3) + lexical(0.1)` + bonus multi-source

**Degradacion elegante:** sin embeddings (L1) solo usa grafo + lexical con warning.

### QRY-001 — RetrieveGraph

Traversal puro del grafo desde un nodo raiz, con profundidad y filtro de edge types.

### QRY-002 — RetrieveSemantic

Busqueda puramente vectorial (solo L2+).

### QRY-004 — RetrieveImpact

Analisis de impacto: dado un nodo, encuentra todos los nodos afectados directa y transitivamente.

- Sigue edges **incoming** (quien depende de este nodo)
- Identifica BDD scenarios a re-ejecutar (edges `VALIDATES`)
- Retorna cadenas de dependencia completas

### QRY-005 — RetrieveCoverage

Validacion de gobernanza: verifica que artefactos relacionados requeridos existan.

Ejemplo: una Entity deberia tener Events, BusinessRules y UseCases asociados.

### QRY-006 — RetrieveViolations

Detecta violaciones de dependencia entre capas (`BR-LAYER-001`):

- Capa inferior no debe referenciar capa superior
- `00-requirements` esta exenta
- Retorna: lista de violaciones, tasa de violacion, total de edges analizados

---

## Entidades de Dominio

### KDDDocument

Representacion parseada de un fichero de spec. Contiene:
- `id`, `kind`, `layer`, `source_path`, `source_hash`
- `front_matter` (dict), `sections` (list[Section]), `wiki_links`

### GraphNode

Nodo del grafo, producido al indexar un KDDDocument:
- ID: `"{Kind}:{DocumentId}"` (ej. `"Entity:Pedido"`, `"Command:CMD-001"`)
- `indexed_fields`: campos extraidos por el extractor especifico del kind

### GraphEdge

Relacion tipada y dirigida entre nodos:
- **Structural** (SCREAMING_SNAKE): `WIKI_LINK`, `ENTITY_RULE`, `UC_EXECUTES_CMD`, `EMITS`, etc.
- **Business** (snake_case): definidos libremente por autores de specs

### Embedding

Vector semantico generado desde un chunk de texto:
- ID: `"{document_id}:{section_path}:{chunk_index}"`
- Modelo por defecto: `all-MiniLM-L6-v2` (384 dimensiones)

### IndexManifest

Metadatos del indice en `manifest.json`: version, nivel, stats, git commit, dominios.

---

## 15 KDDKind Types

Cada kind tiene un extractor dedicado en `application/extractors/kinds/`:

| Kind | Layer | Ejemplo de ID |
|------|-------|---------------|
| `entity` | 01-domain | `Entity:Pedido` |
| `event` | 01-domain | `Event:EVT-Pedido-Created` |
| `business-rule` | 01-domain | `BusinessRule:BR-PEDIDO-001` |
| `business-policy` | 02-behavior | `BusinessPolicy:BP-CREDITO-001` |
| `cross-policy` | 02-behavior | `CrossPolicy:XP-CREDITOS-001` |
| `command` | 02-behavior | `Command:CMD-001` |
| `query` | 02-behavior | `Query:QRY-003` |
| `process` | 02-behavior | `Process:PROC-001` |
| `use-case` | 02-behavior | `UseCase:UC-001` |
| `ui-view` | 03-experience | `UIView:UI-Dashboard` |
| `ui-component` | 03-experience | `UIComponent:UI-Button` |
| `requirement` | 04-verification | `Requirement:REQ-001` |
| `objective` | 00-requirements | `Objective:OBJ-001` |
| `prd` | 00-requirements | `PRD:PRD-KBEngine` |
| `adr` | 00-requirements | `ADR:ADR-0001` |

---

## CLI (`kdd`)

```bash
# Indexar specs (incremental por defecto)
kdd index ./specs/
kdd index ./specs/ --full            # forzar reindex completo
kdd index ./specs/ --domain core     # multi-domain

# Buscar (hibrido: semantica + grafo + lexical)
kdd search "registro de usuario"
kdd search "pedido" --kind entity --kind command
kdd search "autenticacion" --limit 5 --min-score 0.7
kdd search "..." --no-graph          # solo semantica + lexical
kdd search "..." --json-output       # salida JSON

# Explorar grafo
kdd graph Entity:Pedido              # traversal desde nodo
kdd graph Entity:Pedido -d 3         # profundidad 3

# Analisis de impacto
kdd impact Entity:Pedido             # que se rompe si cambio Pedido
kdd impact Entity:Pedido -d 5        # profundidad mayor

# Cobertura de gobernanza
kdd coverage Entity:Pedido           # tiene events, rules, UCs?

# Violaciones de capa
kdd violations                       # edges que violan BR-LAYER-001

# Merge de indices
kdd merge ./dev1/.kdd-index ./dev2/.kdd-index -o ./merged/.kdd-index

# Estado del indice
kdd status
```

---

## Domain Events

El pipeline emite eventos inmutables (frozen dataclasses) durante el ciclo de vida:

| Evento | Cuando |
|--------|--------|
| `DocumentDetected` | Fichero con front-matter valido encontrado |
| `DocumentParsed` | Documento parseado por su extractor |
| `DocumentIndexed` | Pipeline de indexacion completado |
| `DocumentStale` | Documento modificado en disco vs indice |
| `DocumentDeleted` | Documento eliminado del filesystem |
| `MergeRequested` | Merge de indices solicitado |
| `MergeCompleted` | Merge completado exitosamente |
| `QueryReceived` | Query de retrieval recibido |
| `QueryCompleted` | Query resuelto exitosamente |
| `QueryFailed` | Query fallido (validacion o resolucion) |

---

## Business Rules (funciones puras)

Implementadas en `domain/rules.py`, sin I/O ni side-effects:

| Regla | Funcion | Descripcion |
|-------|---------|-------------|
| BR-DOCUMENT-001 | `route_document()` | Determina KDDKind desde front-matter |
| BR-EMBEDDING-001 | `embeddable_sections()` | Secciones embeddables por kind |
| BR-INDEX-001 | `detect_index_level()` | Nivel de indice segun recursos |
| BR-LAYER-001 | `is_layer_violation()` | Valida dependencias entre capas |
| BR-MERGE-001 | `resolve_node_conflict()` | Resolucion de conflictos last-write-wins |

---

## Diferencias con v1 (`kb-engine`)

| Aspecto | v1 (`kb` / `src/kb_engine/`) | v2 (`kdd` / `src/kdd/`) |
|---------|------------------------------|-------------------------|
| **Arquitectura** | Services + Pipelines | Hexagonal CQRS + Ports/Adapters |
| **Storage** | SQLite + ChromaDB + FalkorDB | Filesystem artifacts (`.kdd-index/`) |
| **Grafo** | FalkorDBLite / Neo4j | NetworkX (in-memory, cargado de artifacts) |
| **Vectores** | ChromaDB / Qdrant | HNSWLib (in-memory) |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` | `all-MiniLM-L6-v2` |
| **DB requerida** | Si (SQLite minimo) | No (solo ficheros JSON) |
| **Capacidad** | Fija (todo o nada) | Progresiva (L1 → L2 → L3) |
| **Artifact types** | 6 (entity, use-case, rule, process, event, glossary) | 15 KDDKinds |
| **Extractors** | Genericos | 1 dedicado por kind |
| **CLI** | `kb index/search/sync/status/graph` | `kdd index/search/graph/impact/coverage/violations/merge/status` |
| **Queries** | Vector search + graph opcional | 6 queries especializados + hybrid fusion |
| **Specs** | No | 52 specs KDD trazables |
| **Domain events** | No | Si (10 event types) |
| **DI** | Manual / settings | Container con auto-deteccion |

### Coexistencia

Ambos paquetes coexisten en `pyproject.toml`:

```toml
[project.scripts]
kb = "kb_engine.cli:cli"       # v1
kdd = "kdd.api.cli:cli"        # v2
```

v1 sigue siendo funcional. v2 es la direccion arquitectonica futura.
