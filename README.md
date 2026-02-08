# KB-Engine

Sistema de retrieval de conocimiento para agentes de IA. Indexa documentación estructurada (KDD) y devuelve **referencias** a documentos relevantes, no contenido.

## Concepto

KB-Engine actúa como un "bibliotecario": cuando un agente pregunta algo, responde con URLs y anclas a los documentos relevantes (`file://path/to/doc.md#seccion`), permitiendo que el agente decida qué leer.

```
┌─────────────┐     query      ┌─────────────┐     referencias     ┌─────────────┐
│   Agente    │ ─────────────▶ │  KB-Engine  │ ──────────────────▶ │  Agente lee │
│     IA      │                │ (retrieval) │                     │  documentos │
└─────────────┘                └─────────────┘                     └─────────────┘
```

## Arquitectura

### Dual Stack

| Componente | Local (P2P) | Servidor |
|------------|-------------|----------|
| **Trazabilidad** | SQLite | PostgreSQL |
| **Vectores** | ChromaDB | Qdrant |
| **Grafos** | Kuzu | Neo4j |
| **Embeddings** | sentence-transformers | OpenAI |

### Modelo Distribuido

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Desarrollador 1 │     │  Desarrollador 2 │     │  Desarrollador N │
│  (indexa local)  │     │  (indexa local)  │     │  (indexa local)  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                         ┌──────────────────┐
                         │  Servidor Central │
                         │  (merge + search) │
                         └──────────────────┘
```

Cada desarrollador indexa localmente con embeddings deterministas. El servidor central hace merge y ofrece búsqueda unificada.

## Características

- **Chunking semántico KDD**: Estrategias específicas para entidades, casos de uso, reglas, procesos
- **Soporte ES/EN**: Detecta patrones en español e inglés
- **Grafo de conocimiento**: Entidades, conceptos, eventos y sus relaciones (Kuzu/Neo4j)
- **Smart Ingestion**: Pipeline inteligente con detección de tipo de documento
- **CLI**: Interfaz principal via `kb` command

## Quick Start

### Requisitos

- Python 3.11+
- (Opcional) Docker para modo servidor

### Instalación

```bash
# Clonar
git clone <repository-url>
cd kb-engine

# Entorno virtual
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verificar
pytest tests/ -v
```

### Uso (CLI)

```bash
# Indexar documentos
kb index ./docs/domain/

# Buscar
kb search "¿cómo se registra un usuario?"

# Ver estado
kb status

# Sincronizar con servidor
kb sync --remote https://kb.example.com
```

## Estructura del Proyecto

```
kb-engine/
├── src/kb_engine/
│   ├── core/           # Modelos de dominio e interfaces
│   ├── smart/          # Pipeline de ingesta inteligente (Kuzu)
│   │   ├── parsers/    # Detectores y parsers KDD
│   │   ├── chunking/   # Chunking jerárquico con contexto
│   │   ├── extraction/ # Extracción de entidades para grafo
│   │   ├── stores/     # KuzuGraphStore
│   │   └── pipelines/  # EntityIngestionPipeline
│   ├── repositories/   # Implementaciones de storage
│   ├── chunking/       # Estrategias de chunking clásicas
│   ├── extraction/     # Pipeline de extracción legacy
│   ├── pipelines/      # Pipelines de indexación/retrieval
│   ├── services/       # Lógica de negocio
│   ├── api/            # REST API (FastAPI)
│   └── cli/            # Comandos CLI (Click)
├── tests/
│   ├── unit/
│   └── integration/
└── docs/design/        # ADRs y documentos de diseño
```

## Documentos KDD Soportados

| Tipo | Descripción |
|------|-------------|
| `entity` | Entidades de dominio (Usuario, Producto, etc.) |
| `use-case` | Casos de uso del sistema |
| `rule` | Reglas de negocio |
| `process` | Procesos y flujos |
| `event` | Eventos de dominio |
| `glossary` | Términos y definiciones |

## API

```bash
# Health check
GET /health

# Búsqueda (devuelve referencias)
POST /api/v1/retrieval/search
{
  "query": "registro de usuario",
  "top_k": 5
}

# Indexar documento
POST /api/v1/indexing/documents

# Listar documentos
GET /api/v1/indexing/documents
```

## Tests

```bash
# Todos los tests
pytest tests/ -v

# Solo unitarios
pytest tests/unit/ -v

# Solo integración
pytest tests/integration/ -v

# Con coverage
pytest tests/ --cov=kb_engine
```

## Configuración

Variables de entorno (`.env`):

```bash
# Modo local (por defecto)
KB_PROFILE=local

# Modo servidor
KB_PROFILE=server
DATABASE_URL=postgresql://...
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
OPENAI_API_KEY=sk-...
```

## Roadmap

- [x] Stack local con SQLite + ChromaDB
- [x] Smart ingestion pipeline con Kuzu
- [ ] CLI completo (`kb index/search/sync/status`)
- [ ] Sincronización P2P con servidor
- [ ] Integración MCP para agentes

## Licencia

MIT
