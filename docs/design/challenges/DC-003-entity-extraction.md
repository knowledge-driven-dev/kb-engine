# DC-003: Extracción de Entidades

---
id: DC-003
status: decided
priority: media
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: [ADR-0003]
---

## 1. Contexto

El pipeline de indexación debe extraer entidades y relaciones de la documentación KDD para poblar el grafo de conocimiento. Las entidades incluyen: Entity, Rule, UseCase, Process, Event, etc.

### Requisitos ya definidos

- **Estrategias configurables**: Modelos eficientes (spaCy) o avanzados (LLM externos)
- **Validación humana**: Requerida para curación de entidades extraídas
- **Origen**: La documentación Markdown con front-matter KDD
- **Destino**: Grafo de conocimiento + trazabilidad en PostgreSQL

### Contexto Técnico

- La documentación KDD tiene estructura conocida (front-matter YAML + Markdown)
- El front-matter ya contiene metadatos: id, kind, status, aliases, tags, related
- Las relaciones pueden ser explícitas (campo `related`) o implícitas (enlaces wiki-style `[[Entity]]`)
- El contenido Markdown puede contener tablas, diagramas Mermaid, código

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Extraer entidades del front-matter (estructurado)
- [ ] RF2: Extraer relaciones explícitas del front-matter (campo `related`, `invokes`, `produces`)
- [ ] RF3: Detectar relaciones implícitas en contenido (enlaces `[[Entity]]`)
- [ ] RF4: Extraer entidades mencionadas en texto libre (NER)
- [ ] RF5: Soporte para múltiples estrategias de extracción (configurable)
- [ ] RF6: Generar nodos y edges para el grafo
- [ ] RF7: Registrar trazabilidad (documento → entidad extraída)

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Tiempo de extracción razonable para documentos largos
- [ ] RNF2: Precisión alta para evitar sobrecarga de validación humana
- [ ] RNF3: Estrategias deben ser intercambiables sin cambiar el pipeline

### 2.3 Restricciones

- Debe funcionar offline (opción sin LLM externo)
- La validación humana es obligatoria antes de aprobar entidades
- Debe mantener trazabilidad documento → chunk → entidad

## 3. Opciones Consideradas

### Opción A: Solo Front-matter (Estructurado)

**Descripción**: Extraer únicamente entidades y relaciones del front-matter YAML. No procesar contenido libre.

```python
def extract(doc):
    metadata = parse_frontmatter(doc)
    entity = Entity(
        id=metadata['id'],
        kind=metadata['kind'],
        relations=metadata.get('related', [])
    )
    return entity
```

**Pros**:
- Muy rápido y determinista
- No requiere modelos ML
- Alta precisión (datos estructurados)
- Funciona offline

**Contras**:
- Pierde relaciones implícitas en el contenido
- No detecta entidades mencionadas sin enlace explícito
- Depende de documentación bien estructurada

**Esfuerzo estimado**: Bajo

---

### Opción B: Front-matter + Regex/Patrones

**Descripción**: Front-matter estructurado + detección de patrones conocidos (enlaces wiki, referencias a IDs).

```python
def extract(doc):
    entity = extract_frontmatter(doc)

    # Detectar enlaces wiki [[Entity]]
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', doc.content)

    # Detectar referencias a IDs (UC-*, RUL-*, etc.)
    id_refs = re.findall(r'(UC|RUL|PRC|EVT|ADR)-[\w-]+', doc.content)

    entity.add_relations(wiki_links + id_refs)
    return entity
```

**Pros**:
- Rápido y determinista
- Captura relaciones implícitas comunes
- No requiere modelos ML
- Funciona offline

**Contras**:
- No detecta entidades sin patrón conocido
- Puede generar falsos positivos
- No entiende contexto semántico

**Esfuerzo estimado**: Bajo

---

### Opción C: spaCy NER + Patrones

**Descripción**: Combinar NER de spaCy para entidades genéricas con patrones para entidades KDD.

```python
nlp = spacy.load("es_core_news_lg")

def extract(doc):
    entity = extract_frontmatter(doc)
    entity.add_relations(extract_patterns(doc))

    # NER para entidades adicionales
    spacy_doc = nlp(doc.content)
    for ent in spacy_doc.ents:
        if ent.label_ in ['ORG', 'PRODUCT', 'CONCEPT']:
            entity.add_mention(ent.text, ent.label_)

    return entity
```

**Pros**:
- Detecta entidades no estructuradas
- Modelo local (offline)
- Rápido (spaCy optimizado)
- Extensible con modelos custom

**Contras**:
- Requiere entrenamiento para dominio específico
- Precisión variable en texto técnico
- Más falsos positivos que patrones

**Esfuerzo estimado**: Medio

---

### Opción D: LLM para Extracción Semántica

**Descripción**: Usar LLM (local o API) para extracción de entidades con comprensión semántica.

```python
def extract(doc):
    entity = extract_frontmatter(doc)
    entity.add_relations(extract_patterns(doc))

    # LLM para extracción avanzada
    prompt = f"""
    Extrae entidades y relaciones del siguiente documento KDD:
    {doc.content}

    Tipos de entidades: Entity, Rule, UseCase, Process, Event
    Formato: JSON
    """

    llm_entities = llm.extract(prompt)
    entity.add_extracted(llm_entities)

    return entity
```

**Pros**:
- Comprensión semántica profunda
- Detecta relaciones implícitas complejas
- Puede inferir tipos de entidad
- Muy flexible

**Contras**:
- Más lento y costoso
- Requiere API externa o modelo local grande
- Resultados no deterministas
- Puede alucinar entidades

**Esfuerzo estimado**: Alto

---

### Opción E: Pipeline Configurable Multi-estrategia

**Descripción**: Pipeline que combina todas las estrategias anteriores, configurable por tipo de documento o preferencia.

```python
class ExtractionPipeline:
    def __init__(self, strategies: List[str]):
        self.extractors = [
            FrontmatterExtractor(),  # Siempre
            PatternExtractor() if 'patterns' in strategies else None,
            SpacyExtractor() if 'spacy' in strategies else None,
            LLMExtractor() if 'llm' in strategies else None,
        ]

    def extract(self, doc) -> Entity:
        entity = Entity()
        for extractor in self.extractors:
            if extractor:
                entity.merge(extractor.extract(doc))
        return entity
```

**Pros**:
- Máxima flexibilidad
- Configurable por caso de uso
- Permite degradación graceful (sin LLM)
- Combina precisión estructurada + recall semántico

**Contras**:
- Más complejo de configurar
- Puede generar duplicados (requiere dedup)
- Múltiples modelos = más recursos

**Esfuerzo estimado**: Alto

## 4. Análisis Comparativo

| Criterio | Peso | Front-matter | +Patrones | +spaCy | LLM | Multi-estrategia |
|----------|------|--------------|-----------|--------|-----|------------------|
| Precisión estructurada | 3 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Recall (entidades implícitas) | 2 | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Velocidad | 2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| Offline capable | 2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| Flexibilidad | 2 | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Simplicidad | 2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ |
| **Total ponderado** | | 31 | 35 | 32 | 28 | 35 |

## 5. Preguntas Abiertas

- [ ] ¿Qué porcentaje de relaciones está en front-matter vs contenido libre?
- [ ] ¿Se necesita entrenar modelo spaCy custom para el dominio?
- [ ] ¿Qué LLM usar si se elige esa opción? (GPT-4, Claude, Llama local?)
- [ ] ¿Cómo manejar conflictos entre estrategias (misma entidad, diferentes atributos)?
- [ ] ¿Cuál es el threshold de confianza para auto-aprobar entidades?

## 6. Decisión

> **Estado**: Decidido

**Opción seleccionada**: E (Multi-estrategia) con Front-matter + Patrones como base y LLM opcional

**Justificación**:
- KDD ya tiene estructura rica en front-matter → extracción con 100% confianza
- Patrones capturan referencias wiki-style y IDs KDD en contenido
- LLM solo cuando se necesite enriquecimiento semántico avanzado
- Confianza explícita en cada extracción para priorización
- Deduplicación automática cuando múltiples extractores detectan la misma entidad
- Minimiza costos y latencia al evitar LLM en 90%+ de casos

**ADRs generados**:
- [ADR-0003: Pipeline de Extracción de Entidades Multi-estrategia](../adr/ADR-0003-entity-extraction-pipeline.md)

## 7. Referencias

- [spaCy NER](https://spacy.io/usage/linguistic-features#named-entities)
- [LlamaIndex Entity Extraction](https://docs.llamaindex.ai/en/stable/examples/metadata_extraction/)
- [Knowledge Graph Construction with LLMs](https://arxiv.org/abs/2310.04835)
- [REBEL: Relation Extraction](https://github.com/Babelscape/rebel)
