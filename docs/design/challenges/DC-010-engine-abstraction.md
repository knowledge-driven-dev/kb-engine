# DC-010: Abstracción de Motores

---
id: DC-010
status: decided
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: [ADR-0001]
---

## 1. Contexto

El sistema debe soportar múltiples implementaciones de bases de datos vectoriales (Qdrant, Weaviate, pgvector) y de grafos (Neo4j, NebulaGraph) de forma intercambiable. Se necesita una capa de abstracción que permita cambiar de motor sin modificar la lógica de negocio.

### Requisitos ya definidos

- **Vector DB**: Qdrant, Weaviate, pgvector
- **Graph DB**: Neo4j, NebulaGraph
- **Agnóstico**: El diseño no debe depender de un motor específico

### Contexto Técnico

- Framework: LlamaIndex (tiene abstracciones propias para vector stores)
- Cada motor tiene APIs y capacidades diferentes
- Algunas features pueden no estar disponibles en todos los motores

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Interfaz común para operaciones vectoriales (insert, search, delete)
- [ ] RF2: Interfaz común para operaciones de grafo (create_node, create_edge, traverse)
- [ ] RF3: Configuración de motor por entorno/despliegue
- [ ] RF4: Soporte para capacidades específicas de cada motor (opcional)
- [ ] RF5: Migración de datos entre motores

### 2.2 Requisitos No Funcionales

- [ ] RNF1: La abstracción no debe degradar rendimiento significativamente
- [ ] RNF2: Fácil de extender para nuevos motores
- [ ] RNF3: Testeable con mocks/fakes

### 2.3 Restricciones

- No todos los motores tienen las mismas capacidades
- Las queries de grafo pueden variar significativamente (Cypher vs nGQL)
- LlamaIndex ya tiene abstracciones que podrían aprovecharse

## 3. Opciones Consideradas

### Opción A: Usar Abstracciones de LlamaIndex

**Descripción**: Aprovechar las interfaces de LlamaIndex para vector stores y graph stores.

```python
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.vector_stores.weaviate import WeaviateVectorStore

# Configuración por entorno
if config.vector_db == "qdrant":
    vector_store = QdrantVectorStore(...)
elif config.vector_db == "weaviate":
    vector_store = WeaviateVectorStore(...)

index = VectorStoreIndex.from_vector_store(vector_store)
```

**Pros**:
- Abstracciones ya probadas
- Menos código custom
- Actualizaciones de LlamaIndex incluyen mejoras

**Contras**:
- Dependencia fuerte de LlamaIndex
- Puede no cubrir todas las operaciones necesarias
- Menos control sobre optimizaciones

**Esfuerzo estimado**: Bajo

---

### Opción B: Interfaces Propias (Ports & Adapters)

**Descripción**: Definir interfaces propias e implementar adaptadores para cada motor.

```python
# Puerto (interfaz)
class VectorStore(Protocol):
    async def insert(self, embeddings: List[Embedding]) -> List[str]: ...
    async def search(self, query: Embedding, top_k: int) -> List[Result]: ...
    async def delete(self, ids: List[str]) -> None: ...

class GraphStore(Protocol):
    async def create_node(self, node: Node) -> str: ...
    async def create_edge(self, edge: Edge) -> str: ...
    async def traverse(self, start: str, query: TraversalQuery) -> List[Node]: ...

# Adaptadores
class QdrantAdapter(VectorStore):
    def __init__(self, client: QdrantClient): ...

class Neo4jAdapter(GraphStore):
    def __init__(self, driver: Neo4jDriver): ...
```

**Pros**:
- Control total sobre la interfaz
- Independiente de frameworks externos
- Fácil de testear con mocks
- Puede optimizar para casos de uso específicos

**Contras**:
- Más código que mantener
- Hay que implementar cada adaptador
- Puede reinventar la rueda

**Esfuerzo estimado**: Alto

---

### Opción C: Híbrido (LlamaIndex + Extensiones Propias)

**Descripción**: Usar LlamaIndex donde sea posible, extender con interfaces propias para operaciones no cubiertas.

```python
# Vector: usar LlamaIndex
from llama_index.vector_stores import QdrantVectorStore

# Graph: interfaz propia (LlamaIndex graph stores menos maduros)
class GraphStore(Protocol):
    async def create_node(self, node: Node) -> str: ...
    # ...

class Neo4jGraphStore(GraphStore):
    # Implementación específica
    pass
```

**Pros**:
- Aprovecha lo mejor de LlamaIndex
- Control donde se necesita
- Pragmático

**Contras**:
- Dos modelos de abstracción
- Puede ser confuso qué usar cuándo

**Esfuerzo estimado**: Medio

---

### Opción D: Repository Pattern con Factory

**Descripción**: Patrón Repository con Factory para instanciar la implementación correcta.

```python
class VectorRepository(ABC):
    @abstractmethod
    async def save_embeddings(self, doc_id: str, embeddings: List[Embedding]): ...

    @abstractmethod
    async def search_similar(self, query: Embedding, filters: Filters) -> Results: ...

class VectorRepositoryFactory:
    @staticmethod
    def create(config: Config) -> VectorRepository:
        if config.vector_db == "qdrant":
            return QdrantRepository(config.qdrant)
        elif config.vector_db == "weaviate":
            return WeaviateRepository(config.weaviate)
        # ...

# Uso
repo = VectorRepositoryFactory.create(config)
await repo.save_embeddings(doc_id, embeddings)
```

**Pros**:
- Patrón conocido (DDD)
- Abstracción a nivel de dominio, no de tecnología
- Dependency Injection friendly

**Contras**:
- Más verboso
- Factory puede crecer con muchos motores

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | LlamaIndex | Ports & Adapters | Híbrido | Repository |
|----------|------|------------|------------------|---------|------------|
| Simplicidad inicial | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| Control | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Testabilidad | 3 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Mantenibilidad | 3 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Alineación LlamaIndex | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Total ponderado** | | 26 | 26 | 29 | 32 |

## 5. Preguntas Abiertas

- [ ] ¿Qué operaciones de grafo son críticas? (Cypher es muy diferente a nGQL)
- [ ] ¿LlamaIndex cubre las operaciones de grafo necesarias?
- [ ] ¿Se necesita soporte para transacciones en grafo?
- [ ] ¿Cómo manejar features específicas de un motor? (ej: filtros avanzados de Qdrant)
- [ ] ¿Se prevé añadir más motores en el futuro?

## 6. Decisión

> **Estado**: Decidido

**Opción seleccionada**: D - Repository Pattern con Factory

**Justificación**:
- Control total sobre interfaces específicas del dominio (lifecycle, trazabilidad, comunidades)
- Alineado con DDD - interfaces en términos de dominio, no de tecnología
- Testeable con mocks/fakes sin dependencias externas
- Extensible para nuevos motores
- Inspirado en implementaciones de HippoRAG y GraphRAG

**ADRs generados**:
- [ADR-0001: Repository Pattern para Abstracción de Almacenamiento](../adr/ADR-0001-repository-pattern-for-storage-abstraction.md)

## 7. Referencias

- [LlamaIndex Vector Stores](https://docs.llamaindex.ai/en/stable/module_guides/storing/vector_stores/)
- [Ports and Adapters (Hexagonal Architecture)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Qdrant Python Client](https://qdrant.tech/documentation/quick-start/)
