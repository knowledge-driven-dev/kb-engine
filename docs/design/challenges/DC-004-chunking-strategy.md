# DC-004: Estrategia de Chunking

---
id: DC-004
status: decided
priority: media
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: [ADR-0002]
---

## 1. Contexto

El chunking determina cómo se dividen los documentos en fragmentos para generar embeddings. Como las fuentes son conocidas (documentación KDD con estructura predefinida), podemos diseñar un chunking preciso y semánticamente coherente.

### Requisitos ya definidos

- **Chunking preciso**: Las fuentes son conocidas (estructura KDD)
- **Trazabilidad**: Cada chunk debe estar vinculado a su documento origen
- **Tipos de documento**: Múltiples (Entity, Rule, UseCase, Process, API, etc.)

### Contexto Técnico

- Documentos Markdown con front-matter YAML
- Estructura conocida: secciones H2, tablas, diagramas Mermaid, código
- Embeddings almacenados en Vector DB (Qdrant/Weaviate/pgvector)
- El chunk es la unidad mínima de retrieval

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Chunking específico por tipo de documento KDD
- [ ] RF2: Preservar coherencia semántica (no cortar mitad de frase)
- [ ] RF3: Incluir metadatos del documento en cada chunk
- [ ] RF4: Manejar contenido especial (tablas, código, Mermaid)
- [ ] RF5: Chunks con overlap configurable
- [ ] RF6: Registrar posición del chunk en documento origen

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Tamaño de chunk optimizado para el modelo de embedding
- [ ] RNF2: Balance entre granularidad y contexto
- [ ] RNF3: Rendimiento en documentos largos

### 2.3 Restricciones

- Tamaño máximo de chunk limitado por modelo de embedding (ej: 512 tokens)
- Debe mantener trazabilidad para actualizaciones incrementales
- Compatible con todos los tipos de documento KDD

## 3. Opciones Consideradas

### Opción A: Chunking por Tamaño Fijo

**Descripción**: Dividir documentos en chunks de tamaño fijo (tokens o caracteres) con overlap.

```python
def chunk_fixed(doc, size=512, overlap=50):
    tokens = tokenize(doc.content)
    chunks = []
    for i in range(0, len(tokens), size - overlap):
        chunks.append(tokens[i:i + size])
    return chunks
```

**Pros**:
- Simple de implementar
- Predecible en tamaño
- Funciona para cualquier documento

**Contras**:
- Rompe coherencia semántica
- No aprovecha estructura conocida
- Puede cortar tablas, código, listas

**Esfuerzo estimado**: Bajo

---

### Opción B: Chunking por Secciones (H2/H3)

**Descripción**: Usar la estructura Markdown (headers) como delimitadores naturales.

```python
def chunk_by_sections(doc):
    chunks = []
    current = {"header": None, "content": ""}

    for line in doc.content.split('\n'):
        if line.startswith('## '):
            if current["content"]:
                chunks.append(current)
            current = {"header": line, "content": ""}
        else:
            current["content"] += line + '\n'

    return chunks
```

**Pros**:
- Coherencia semántica (sección = concepto)
- Aprovecha estructura KDD
- Metadatos naturales (título de sección)

**Contras**:
- Secciones muy largas exceden límite
- Secciones muy cortas desperdician contexto
- No maneja bien documentos sin estructura

**Esfuerzo estimado**: Bajo

---

### Opción C: Chunking Semántico por Tipo de Documento

**Descripción**: Estrategia de chunking específica para cada tipo de documento KDD.

```python
chunking_strategies = {
    "entity": EntityChunker(),      # Atributos, Relaciones, Ciclo de vida como chunks separados
    "use_case": UseCaseChunker(),   # Flujo principal, Extensiones, Pre/Post condiciones
    "rule": RuleChunker(),          # Tabla de decisión como un chunk
    "process": ProcessChunker(),    # Pasos del proceso, diagrama
    "api": ApiChunker(),            # Endpoints como chunks individuales
}

def chunk(doc):
    strategy = chunking_strategies.get(doc.kind, DefaultChunker())
    return strategy.chunk(doc)
```

**Pros**:
- Máxima coherencia semántica
- Chunks alineados con estructura KDD
- Optimizado para cada tipo de contenido

**Contras**:
- Requiere implementar N estrategias
- Más complejo de mantener
- Documentos híbridos pueden ser problemáticos

**Esfuerzo estimado**: Alto

---

### Opción D: Chunking Jerárquico (Multi-nivel)

**Descripción**: Crear chunks a múltiples niveles de granularidad (documento, sección, párrafo).

```python
def chunk_hierarchical(doc):
    chunks = []

    # Nivel 1: Documento completo (resumen)
    chunks.append(Chunk(level=1, content=doc.summary, parent=None))

    # Nivel 2: Secciones
    for section in doc.sections:
        section_chunk = Chunk(level=2, content=section, parent=doc.id)
        chunks.append(section_chunk)

        # Nivel 3: Párrafos/items
        for para in section.paragraphs:
            chunks.append(Chunk(level=3, content=para, parent=section_chunk.id))

    return chunks
```

**Pros**:
- Retrieval a diferentes niveles de detalle
- Permite navegación jerárquica
- Contexto disponible en chunks padre

**Contras**:
- Más embeddings = más almacenamiento y costo
- Retrieval más complejo (qué nivel usar?)
- Mayor complejidad de trazabilidad

**Esfuerzo estimado**: Alto

---

### Opción E: Híbrido (Secciones + Subdivisión si excede)

**Descripción**: Chunking por secciones, con subdivisión automática si excede el límite.

```python
def chunk_hybrid(doc, max_tokens=512, overlap=50):
    chunks = []

    for section in split_by_headers(doc):
        if token_count(section) <= max_tokens:
            chunks.append(section)
        else:
            # Subdividir sección larga preservando párrafos
            chunks.extend(
                split_preserving_paragraphs(section, max_tokens, overlap)
            )

    return chunks
```

**Pros**:
- Balance entre coherencia y límites técnicos
- Aprovecha estructura cuando es posible
- Fallback robusto para secciones largas

**Contras**:
- Comportamiento menos predecible
- Chunks de tamaños variables

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Fijo | Secciones | Por Tipo | Jerárquico | Híbrido |
|----------|------|------|-----------|----------|------------|---------|
| Coherencia semántica | 3 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Simplicidad | 2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ |
| Aprovecha estructura KDD | 3 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Manejo de límites | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Costo almacenamiento | 2 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| **Total ponderado** | | 22 | 25 | 30 | 27 | 32 |

## 5. Preguntas Abiertas

- [ ] ¿Qué modelo de embedding se usará? (determina tamaño máximo de chunk)
- [ ] ¿Cómo manejar tablas que exceden el límite de tokens?
- [ ] ¿Los diagramas Mermaid se incluyen como texto o se ignoran?
- [ ] ¿Se necesita chunking jerárquico para navegación o solo plano?
- [ ] ¿Cuál es el overlap óptimo para el dominio?

## 6. Decisión

> **Estado**: Decidido

**Opción seleccionada**: C (Por tipo KDD) + E (Híbrido) combinados

**Justificación**:
- Conocemos la estructura KDD → chunking semántico inteligente
- Cada tipo de documento tiene su estrategia especializada
- Metadatos ricos (chunk_type) permiten retrieval más preciso
- Fallback con subdivisión si excede límite de tokens
- Inspirado en GraphRAG TextUnits

**ADRs generados**:
- [ADR-0002: Estrategia de Chunking Semántico por Tipo KDD](../adr/ADR-0002-kdd-semantic-chunking-strategy.md)

## 7. Referencias

- [LlamaIndex Node Parsers](https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/)
- [Chunking Strategies for RAG](https://www.pinecone.io/learn/chunking-strategies/)
- [Semantic Chunking](https://python.langchain.com/docs/modules/data_connection/document_transformers/semantic-chunker)
- [RAPTOR: Recursive Abstractive Processing](https://arxiv.org/abs/2401.18059)
