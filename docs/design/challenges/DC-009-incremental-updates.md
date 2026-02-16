# DC-009: Actualización Incremental

---
id: DC-009
status: open
priority: media
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

Cuando un documento cambia, el sistema debe actualizar eficientemente los chunks, embeddings y nodos derivados sin reindexar todo. La trazabilidad (ver sección 4 de requirements.md) permite identificar qué elementos derivan de cada documento.

### Requisitos ya definidos

- **Trazabilidad total**: Document → Chunks → Embeddings → Nodes
- **Hash de documentos**: Para detectar cambios
- **Actualización precisa**: A nivel de chunk si es posible

### Contexto Técnico

- Documentos Markdown con estructura conocida (KDD)
- Chunks tienen hash y posición en documento
- Cada chunk tiene 1 embedding asociado
- Cada documento puede generar múltiples nodos

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Detectar si un documento ha cambiado (hash comparison)
- [ ] RF2: Identificar qué chunks cambiaron dentro de un documento
- [ ] RF3: Actualizar solo los embeddings de chunks modificados
- [ ] RF4: Actualizar nodos afectados por cambios en contenido
- [ ] RF5: Mantener trazabilidad durante actualización
- [ ] RF6: Soporte para rollback si la actualización falla

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Tiempo de actualización proporcional al cambio, no al tamaño total
- [ ] RNF2: No interrumpir consultas durante actualización
- [ ] RNF3: Consistencia eventual aceptable

### 2.3 Restricciones

- Los IDs de chunks pueden cambiar si la estructura del documento cambia
- Los embeddings dependen del contenido exacto del chunk
- Los nodos pueden tener relaciones con otros nodos no afectados

## 3. Opciones Consideradas

### Opción A: Reindexación Completa del Documento

**Descripción**: Ante cualquier cambio, eliminar todo lo derivado y reindexar completamente.

```python
async def update_document(doc_id, new_content):
    # Eliminar todo lo anterior
    await delete_document_cascade(doc_id)

    # Reindexar completo
    await index_document(new_content)
```

**Pros**:
- Simple de implementar
- Garantiza consistencia
- No hay lógica de diff compleja

**Contras**:
- Ineficiente para cambios pequeños
- Pérdida temporal de disponibilidad
- No escala con documentos grandes

**Esfuerzo estimado**: Bajo

---

### Opción B: Diff a Nivel de Chunk (Content Hash)

**Descripción**: Comparar hashes de chunks para identificar cambios.

```python
async def update_document(doc_id, new_content):
    old_chunks = await get_chunks(doc_id)
    new_chunks = chunk_document(new_content)

    old_hashes = {c.hash: c for c in old_chunks}
    new_hashes = {c.hash: c for c in new_chunks}

    # Chunks a eliminar (hash ya no existe)
    to_delete = set(old_hashes.keys()) - set(new_hashes.keys())

    # Chunks a crear (hash nuevo)
    to_create = set(new_hashes.keys()) - set(old_hashes.keys())

    # Chunks sin cambios (hash existe en ambos)
    unchanged = set(old_hashes.keys()) & set(new_hashes.keys())

    await delete_chunks(to_delete)
    await create_chunks(to_create)
    # unchanged: no hacer nada
```

**Pros**:
- Solo procesa lo que cambió
- Eficiente para cambios localizados
- Hash es determinista

**Contras**:
- Si cambia estructura, muchos hashes cambian
- No detecta reordenamiento (mismo contenido, diferente posición)
- Puede perder contexto si chunks adyacentes cambian

**Esfuerzo estimado**: Medio

---

### Opción C: Diff Semántico (Similarity Threshold)

**Descripción**: Comparar chunks por similitud semántica para detectar cambios menores.

```python
async def update_document(doc_id, new_content):
    old_chunks = await get_chunks_with_embeddings(doc_id)
    new_chunks = chunk_document(new_content)

    matched = []
    for new_chunk in new_chunks:
        new_embedding = generate_embedding(new_chunk)
        best_match = find_most_similar(new_embedding, old_chunks)

        if best_match.similarity > THRESHOLD:
            # Chunk similar encontrado - actualizar si hay diferencias menores
            matched.append((new_chunk, best_match))
        else:
            # Chunk nuevo
            await create_chunk(new_chunk)

    # Old chunks no matcheados → eliminar
```

**Pros**:
- Tolera cambios menores (typos, reformulaciones)
- Puede preservar embeddings casi idénticos
- Más inteligente que hash puro

**Contras**:
- Más lento (requiere comparación de embeddings)
- Threshold difícil de calibrar
- Puede generar falsos positivos/negativos

**Esfuerzo estimado**: Alto

---

### Opción D: Versionado de Chunks (Append-Only)

**Descripción**: Nunca eliminar, solo marcar versiones y crear nuevas.

```python
async def update_document(doc_id, new_content):
    # Marcar versión actual como histórica
    await mark_chunks_as_historical(doc_id, version=current_version)

    # Crear nueva versión
    new_version = current_version + 1
    new_chunks = chunk_document(new_content)
    await create_chunks(new_chunks, version=new_version)

    # Actualizar puntero de versión activa
    await set_active_version(doc_id, new_version)

    # Cleanup async (eliminar versiones antiguas después de N días)
```

**Pros**:
- Historial completo de cambios
- Rollback trivial (cambiar versión activa)
- No hay eliminación durante update

**Contras**:
- Más almacenamiento
- Queries deben filtrar por versión
- Cleanup necesario

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Reindex Completo | Diff Hash | Diff Semántico | Versionado |
|----------|------|------------------|-----------|----------------|------------|
| Eficiencia | 3 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Simplicidad | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| Consistencia | 3 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Rollback | 2 | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ |
| Historial | 1 | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ |
| **Total ponderado** | | 21 | 25 | 20 | 28 |

## 5. Preguntas Abiertas

- [ ] ¿Qué tan frecuentes son las actualizaciones de documentos?
- [ ] ¿Se necesita historial de versiones para auditoría?
- [ ] ¿Cuál es el tamaño promedio de cambio? (typo vs reescritura completa)
- [ ] ¿Los nodos del grafo deben versionarse también?
- [ ] ¿Se requiere diff visual para el Knowledge Manager?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [Vector DB Update Strategies](https://www.pinecone.io/learn/vector-database/)
- [Content-Addressable Storage](https://en.wikipedia.org/wiki/Content-addressable_storage)
- [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
