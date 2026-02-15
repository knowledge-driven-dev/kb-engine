---
id: BR-MERGE-001
kind: business-rule
title: Merge Conflict Resolution
category: state
severity: high
status: draft
---

# BR-MERGE-001 — Merge Conflict Resolution

## Declaración

Cuando el servidor ejecuta un merge de [[IndexManifest|índices]] de múltiples desarrolladores ([[EVT-Index-MergeRequested]]), pueden existir conflictos: el mismo [[GraphNode]] modificado por diferentes desarrolladores. El sistema resuelve estos conflictos con una estrategia **last-write-wins por nodo** con detección y reporte.

### Reglas de merge

1. **Nodos sin conflicto** (presentes en un solo índice): se copian directamente al índice mergeado.
2. **Nodos idénticos** (mismo `source_hash` en todos los índices): se toma cualquier copia (son equivalentes).
3. **Nodos en conflicto** (diferente `source_hash` entre índices): se aplica **last-write-wins** basándose en el `indexed_at` más reciente.
4. **Nodos eliminados** en un índice pero presentes en otro: la eliminación gana (delete-wins). Si el nodo fue modificado después de la eliminación en otro índice, se emite un warning.

### Merge de edges

Los [[GraphEdge|edges]] se mergean por unión: todos los edges de todos los índices se incluyen, eliminando duplicados exactos (`from_node` + `to_node` + `edge_type`). Si un nodo fue eliminado, sus edges se eliminan en cascada.

### Merge de embeddings

Los [[Embedding|embeddings]] asociados a un nodo en conflicto se reemplazan completos por los del nodo ganador (el más reciente). No se hace merge parcial de embeddings.

### Validación de compatibilidad

Antes de ejecutar el merge, los manifiestos deben ser compatibles:
- Misma `version` major (e.g. `1.x` con `1.y` es compatible, `1.x` con `2.x` no).
- Mismo `embedding_model` si ambos índices son ≥ L2 (vectores de modelos diferentes no son comparables).
- Misma `structure` (`single-domain` con `single-domain`, `multi-domain` con `multi-domain`).

## Por qué existe

En un entorno distribuido donde múltiples desarrolladores indexan en local y hacen push, es inevitable que dos personas modifiquen la misma spec. Sin una estrategia de resolución definida, el merge produciría duplicados o errores.

## Cuándo aplica

Durante la ejecución de [[CMD-004-MergeIndex]] en el servidor, cuando se reciben dos o más `.kdd-index/` de diferentes desarrolladores.

## Qué pasa si se incumple

- Si los manifiestos no son compatibles y se intenta el merge, se producen vectores de embeddings incomparables o nodos con schemas diferentes.
- Si no se aplica last-write-wins, se podrían perder cambios del desarrollador que indexó más recientemente.

## Ejemplos

**Merge sin conflictos:**
```
Dev A: indexó Pedido.md (hash: abc123) + Reto.md (hash: def456)
Dev B: indexó Usuario.md (hash: ghi789)
→ Merge: 3 nodos, 0 conflictos
```

**Merge con conflicto — last-write-wins:**
```
Dev A: indexó Pedido.md (hash: abc123, indexed_at: 10:00)
Dev B: indexó Pedido.md (hash: xyz999, indexed_at: 10:15)
→ Conflicto en Entity:Pedido
→ Ganador: Dev B (indexed_at más reciente)
→ conflicts_resolved: 1
```

**Merge con eliminación:**
```
Dev A: eliminó Pedido.md (nodo ausente en su índice)
Dev B: tiene Pedido.md sin cambios (hash: abc123)
→ Delete-wins: Entity:Pedido se elimina del índice mergeado
→ Edges de Entity:Pedido eliminados en cascada
```

**Merge incompatible (rechazado):**
```
Dev A: manifest.embedding_model = "nomic-embed-text-v1.5"
Dev B: manifest.embedding_model = "bge-small-en-v1.5"
→ Error: "Incompatible embedding models, cannot merge"
→ EVT-Index-MergeCompleted no se emite
```
