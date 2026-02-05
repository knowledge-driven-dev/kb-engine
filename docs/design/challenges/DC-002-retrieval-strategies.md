# DC-002: Estrategias de Retrieval

---
id: DC-002
status: open
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El sistema RAG híbrido combina búsqueda vectorial (semántica) con búsqueda en grafos (relaciones). La estrategia de retrieval determina cómo se combinan ambos motores para obtener los resultados más relevantes.

### Requisitos ya definidos

- **Estrategia principal**: Grafo primero (expande contexto) → Vector (búsqueda semántica)
- **Múltiples algoritmos**: Configurables y seleccionables en runtime
- **Selección automática**: Un algoritmo (posiblemente LLM pequeño) detecta el tipo de conversación y selecciona la estrategia óptima
- **Estrategia por defecto**: Inspirada en papers de referencia
- **Latencia**: Muy baja (prioridad)

### Contexto Técnico

- Framework: LlamaIndex (Python)
- Vector DB: Qdrant / Weaviate / pgvector
- Graph DB: Neo4j / NebulaGraph
- Modelo de conocimiento: Entidades KDD (Entity, Rule, UseCase, Process, etc.)

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Soportar múltiples estrategias de retrieval
- [ ] RF2: Permitir selección de estrategia en runtime (por query)
- [ ] RF3: Implementar selector automático de estrategia
- [ ] RF4: Estrategia híbrida: grafo expande → vector busca
- [ ] RF5: Configuración de estrategia por defecto
- [ ] RF6: Soporte para filtros de seguridad (RBAC) en retrieval

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Latencia de retrieval < X ms (por definir)
- [ ] RNF2: Estrategias deben ser extensibles (plugin architecture)
- [ ] RNF3: Métricas de rendimiento por estrategia

### 2.3 Restricciones

- Debe funcionar con cualquier combinación de Vector DB + Graph DB soportada
- El selector automático no debe añadir latencia significativa
- Compatible con el modelo de trazabilidad (resultados deben poder rastrearse)

## 3. Opciones Consideradas

### Opción A: Estrategias Hardcoded

**Descripción**: Implementar un conjunto fijo de estrategias predefinidas. El cliente selecciona por nombre.

```python
strategies = {
    "vector_only": VectorOnlyStrategy(),
    "graph_only": GraphOnlyStrategy(),
    "hybrid_graph_first": HybridGraphFirstStrategy(),
    "hybrid_vector_first": HybridVectorFirstStrategy(),
}
```

**Pros**:
- Simple de implementar
- Comportamiento predecible
- Fácil de testear

**Contras**:
- Poco flexible
- Requiere redeploy para nuevas estrategias
- No permite customización por cliente

**Esfuerzo estimado**: Bajo

---

### Opción B: Strategy Pattern + Registry

**Descripción**: Patrón Strategy con registro dinámico. Las estrategias implementan una interfaz común y se registran en runtime.

```python
class RetrievalStrategy(Protocol):
    def retrieve(self, query: Query, context: Context) -> Results: ...

class StrategyRegistry:
    def register(self, name: str, strategy: RetrievalStrategy): ...
    def get(self, name: str) -> RetrievalStrategy: ...
```

**Pros**:
- Extensible sin modificar código core
- Permite estrategias custom por despliegue
- Testeable con mocks

**Contras**:
- Más complejo que hardcoded
- Requiere documentación de la interfaz

**Esfuerzo estimado**: Medio

---

### Opción C: Pipeline Configurable (LlamaIndex-style)

**Descripción**: Definir retrieval como un pipeline de pasos configurables. Cada paso es un componente (retriever, reranker, filter).

```python
pipeline = RetrievalPipeline([
    GraphExpander(depth=2, relations=["RELATES_TO", "INVOKES"]),
    VectorRetriever(top_k=10),
    SecurityFilter(),
    Reranker(model="cross-encoder"),
])
```

**Pros**:
- Muy flexible y composable
- Alineado con arquitectura LlamaIndex
- Permite experimentación fácil

**Contras**:
- Más complejo de configurar
- Puede ser difícil de depurar
- Overhead de pipeline

**Esfuerzo estimado**: Alto

---

### Opción D: Híbrido (Registry + Pipelines predefinidos)

**Descripción**: Estrategias predefinidas como pipelines, pero con registry para extensibilidad.

```python
# Estrategias predefinidas como pipelines
default_strategies = {
    "semantic": Pipeline([VectorRetriever(top_k=20)]),
    "graph_traverse": Pipeline([GraphTraverser(depth=3)]),
    "hybrid": Pipeline([GraphExpander(), VectorRetriever(), Reranker()]),
}

# Registry permite añadir custom
registry.register("custom_client", custom_pipeline)
```

**Pros**:
- Balance entre simplicidad y flexibilidad
- Estrategias por defecto listas para usar
- Extensible para casos avanzados

**Contras**:
- Dos modelos mentales (estrategias vs pipelines)

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Hardcoded | Strategy+Registry | Pipeline | Híbrido |
|----------|------|-----------|-------------------|----------|---------|
| Simplicidad inicial | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| Extensibilidad | 3 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Alineación LlamaIndex | 2 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Facilidad de configuración | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| Rendimiento | 3 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Total ponderado** | | 26 | 31 | 27 | 30 |

## 5. Preguntas Abiertas

- [ ] ¿Qué papers de referencia usar para la estrategia por defecto? (GraphRAG, RAPTOR, HippoRAG?)
- [ ] ¿Qué modelo usar para el selector automático? (clasificador, LLM pequeño, heurísticas?)
- [ ] ¿Cuál es el SLA de latencia aceptable para retrieval?
- [ ] ¿Se necesita A/B testing entre estrategias?
- [ ] ¿Las estrategias deben ser configurables por proyecto/dominio?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [GraphRAG (Microsoft)](https://arxiv.org/abs/2404.16130) - Graph-based RAG
- [RAPTOR](https://arxiv.org/abs/2401.18059) - Recursive Abstractive Processing
- [HippoRAG](https://arxiv.org/abs/2405.14831) - Neurobiologically inspired RAG
- [LlamaIndex Query Pipelines](https://docs.llamaindex.ai/en/stable/module_guides/querying/pipeline/)
- [Hybrid Search patterns](https://www.pinecone.io/learn/hybrid-search/)
