# DC-011: Ciclo de Vida del Contenido

---
id: DC-011
status: open
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El contenido indexado en el sistema tiene un ciclo de vida que refleja el estado del desarrollo del software que documenta. Un documento puede estar en desarrollo (`dev`), pendiente de despliegue, o en producción (`pro`). Este estado debe propagarse a todos los elementos derivados (chunks, embeddings, nodos) para que las queries puedan filtrar según el contexto.

### Integración con Git

La documentación source está versionada en Git. El sistema debe:
- Saber qué versión (commit/tag/branch) de cada documento tiene indexada
- No necesariamente tener la última versión (por eficiencia, solo cargamos lo necesario)
- Poder distinguir entre versiones indexadas y versiones disponibles en Git
- Sincronizar el `lifecycle_state` con el flujo de Git (ej: `main` → pro, `develop` → dev)

### Caso de Uso Principal

1. Se indexa un nuevo requisito funcional desde branch `develop` con estado `dev`
2. Se guarda: `git_ref=develop`, `git_commit_sha=abc123`, `lifecycle_state=dev`
3. Todos los chunks, embeddings y nodos heredan el estado `dev`
4. Las queries de retrieval en contexto de desarrollo incluyen contenido `dev` + `pro`
5. Las queries en contexto de producción solo incluyen contenido `pro`
6. El documento se mergea a `main` y se hace tag `v1.2.0`
7. Se reindexar desde `main` o tag → `lifecycle_state` pasa a `pro`

### Requisitos ya definidos

- **Trazabilidad total**: Document → Chunks → Embeddings → Nodes
- **RBAC**: Filtros de seguridad en queries
- **Separación indexación/retrieval**: El estado es un filtro más en retrieval
- **Git como source**: Documentación versionada en repositorio Git

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Definir estados del ciclo de vida del contenido
- [ ] RF2: Asignar estado al documento en momento de indexación
- [ ] RF3: Propagar estado a chunks, embeddings y nodos derivados
- [ ] RF4: Filtrar por estado en queries de retrieval
- [ ] RF5: Permitir transiciones de estado (dev → staging → pro)
- [ ] RF6: Propagar cambios de estado a elementos derivados
- [ ] RF7: Registrar git_ref, git_commit_sha de cada documento indexado
- [ ] RF8: Detectar si el documento indexado está desactualizado vs Git
- [ ] RF9: Mapeo configurable entre git_ref y lifecycle_state (ej: main→pro, develop→dev)

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Cambio de estado no debe requerir reindexación
- [ ] RNF2: Filtro por estado no debe impactar latencia significativamente
- [ ] RNF3: Auditoría de transiciones de estado

### 2.3 Restricciones

- El estado es un atributo más, como la seguridad (RBAC)
- Debe funcionar en las 3 BBDDs (PostgreSQL, Vector, Graph)
- Compatible con el modelo de trazabilidad existente

## 3. Opciones Consideradas

### Opción A: Estado Simple (Campo Único)

**Descripción**: Un campo `state` en cada entidad con valores fijos.

```python
class ContentState(Enum):
    DEV = "dev"          # En desarrollo
    STAGING = "staging"  # Pendiente de despliegue
    PRO = "pro"          # En producción
    DEPRECATED = "deprecated"  # Obsoleto

# En Document, Chunk, Embedding, GraphNode
class Document:
    id: str
    content: str
    state: ContentState  # Heredado por derivados

# Query con filtro
async def search(query, state_filter: List[ContentState]):
    return await vector_db.search(
        query,
        filters={"state": {"$in": state_filter}}
    )
```

**Pros**:
- Simple de implementar
- Fácil de entender
- Filtrado eficiente (índice en campo)

**Contras**:
- No soporta múltiples versiones simultáneas
- Un documento solo puede estar en un estado
- Cambio de estado afecta a todos los derivados inmediatamente

**Esfuerzo estimado**: Bajo

---

### Opción B: Estado + Versión (Branching)

**Descripción**: Combinar estado con versión, permitiendo múltiples "ramas" del contenido.

```python
class Document:
    id: str
    content: str
    branch: str          # "main", "feature-x", "release-1.2"
    state: ContentState  # Estado dentro del branch
    version: int         # Versión dentro del branch

# Un documento puede existir en múltiples branches
# main/pro/v3, feature-x/dev/v1

# Query con filtro de branch + estado
async def search(query, branch: str = "main", states: List[ContentState] = ["pro"]):
    return await vector_db.search(
        query,
        filters={
            "branch": branch,
            "state": {"$in": states}
        }
    )
```

**Pros**:
- Soporta desarrollo paralelo (branches)
- Versionado explícito
- Similar a Git (modelo mental conocido)

**Contras**:
- Más complejo
- Más almacenamiento (contenido duplicado por branch)
- Merge entre branches puede ser complejo

**Esfuerzo estimado**: Alto

---

### Opción C: Tags/Labels (Multi-estado)

**Descripción**: Usar etiquetas múltiples en lugar de estado único.

```python
class Document:
    id: str
    content: str
    labels: Set[str]  # {"dev", "sprint-23", "feature-auth", "reviewed"}

# Query con filtro de labels
async def search(query, required_labels: Set[str], excluded_labels: Set[str] = None):
    filters = {"labels": {"$all": required_labels}}
    if excluded_labels:
        filters["labels"]["$nin"] = excluded_labels
    return await vector_db.search(query, filters=filters)

# Ejemplos:
# - Producción: required={"pro"}
# - Dev de feature auth: required={"dev", "feature-auth"}
# - Todo menos deprecated: excluded={"deprecated"}
```

**Pros**:
- Muy flexible
- Soporta múltiples dimensiones (estado, feature, sprint, etc.)
- No hay transiciones rígidas

**Contras**:
- Puede volverse caótico sin gobernanza
- Más difícil de razonar sobre "estado actual"
- Queries de labels pueden ser menos eficientes

**Esfuerzo estimado**: Medio

---

### Opción D: Estado con Herencia Configurable

**Descripción**: Estado en documento con reglas de herencia configurables para derivados.

```python
class Document:
    id: str
    state: ContentState
    state_inheritance: InheritancePolicy  # ALL, NONE, CUSTOM

class InheritancePolicy(Enum):
    ALL = "all"      # Todos los derivados heredan
    NONE = "none"    # Derivados tienen su propio estado
    CUSTOM = "custom"  # Reglas específicas

# Configuración de herencia
inheritance_rules = {
    "chunks": "inherit",      # Siempre hereda de documento
    "embeddings": "inherit",  # Siempre hereda de chunk
    "nodes": "independent",   # Nodos pueden tener estado propio
}

# Esto permite que un nodo (entidad de negocio) esté en PRO
# aunque el documento que lo define esté en DEV (actualización)
```

**Pros**:
- Flexibilidad controlada
- Soporta casos donde nodos trascienden documentos
- Permite evolución independiente de entidades

**Contras**:
- Más complejo de implementar
- Reglas de herencia pueden ser confusas
- Queries más complejas

**Esfuerzo estimado**: Alto

---

### Opción E: Estado basado en Git Ref (Git-Native)

**Descripción**: El `lifecycle_state` se deriva automáticamente de la `git_ref` desde la que se indexó, con mapeo configurable.

```python
# Configuración de mapeo git_ref → lifecycle_state
git_lifecycle_mapping = {
    "main": "pro",
    "master": "pro",
    "develop": "dev",
    "release/*": "staging",
    "feature/*": "dev",
    "hotfix/*": "staging",
    # Tags
    "v*": "pro",  # Cualquier tag que empiece con v
}

class Document:
    id: str
    content: str
    git_repo: str
    git_ref: str              # branch, tag, o commit
    git_commit_sha: str       # SHA exacto
    git_ref_type: str         # 'branch' | 'tag' | 'commit'

    @property
    def lifecycle_state(self) -> str:
        # Derivado del git_ref según mapeo
        return resolve_lifecycle_from_git_ref(self.git_ref, git_lifecycle_mapping)

# Reindexar desde otra ref = cambio automático de lifecycle
async def reindex_document(doc_id, new_git_ref):
    content = await git.fetch(doc.git_repo, doc.external_ref, new_git_ref)
    doc.git_ref = new_git_ref
    doc.git_commit_sha = await git.resolve_sha(new_git_ref)
    # lifecycle_state se actualiza automáticamente
    await propagate_state_to_derived(doc)
```

**Pros**:
- Alineado con flujo de desarrollo (GitFlow, trunk-based)
- Estado derivado, no duplicado
- Cambio de estado = reindexar desde otra ref (operación natural)
- Auditoría implícita (commit SHA)

**Contras**:
- Requiere convenciones de Git (naming de branches/tags)
- Menos flexible para estados que no mapean a Git
- Override manual requiere campo adicional

**Esfuerzo estimado**: Medio

---

### Opción F: Doble Estado (Lifecycle + Sync)

**Descripción**: Separar el estado del documento (lifecycle) del estado del pipeline (sync).

```python
class Document:
    id: str
    content: str

    # Git tracking
    git_ref: str
    git_commit_sha: str

    # Estado de lifecycle (negocio) - puede derivarse de git_ref o ser manual
    lifecycle_state: LifecycleState  # dev, staging, pro, deprecated

    # Estado de pipeline (técnico)
    sync_state: SyncState  # pending, indexed, failed, outdated

class Chunk:
    id: str
    document_id: str
    lifecycle_state: LifecycleState  # Heredado de documento
    # sync_state no aplica a chunks

# Query filtra por lifecycle_state
# Pipeline usa sync_state para saber qué procesar
# sync_state = 'outdated' cuando git tiene versión más nueva
```

**Pros**:
- Separación clara de concerns
- Estado de negocio vs estado técnico
- Lifecycle se propaga, sync es local
- Combina bien con Git tracking

**Contras**:
- Dos campos de estado
- Puede confundir inicialmente

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Simple | Branch+Ver | Tags | Herencia | Git-Native | Doble Estado |
|----------|------|--------|------------|------|----------|------------|--------------|
| Simplicidad | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| Flexibilidad | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Rendimiento queries | 3 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Modelo mental claro | 3 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Integración Git | 3 | ⭐ | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| Soporte multi-versión | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Total ponderado** | | 32 | 32 | 30 | 26 | 39 | 35 |

## 5. Preguntas Abiertas

### Lifecycle States
- [ ] ¿Cuáles son los estados exactos del ciclo de vida? (dev, staging, pro, deprecated, ¿otros?)
- [ ] ¿Un documento puede estar en múltiples estados simultáneamente?
- [ ] ¿Se necesita historial de transiciones de estado (auditoría)?
- [ ] ¿Quién puede cambiar el estado? (¿rol específico, automático por CI/CD?)

### Integración Git
- [ ] ¿Cómo mapear git_ref a lifecycle_state? (ej: main→pro, develop→dev, feature/*→dev)
- [ ] ¿El cambio de estado es automático al reindexar desde otra ref, o manual?
- [ ] ¿Debemos detectar proactivamente que hay versiones más nuevas en Git?
- [ ] ¿Cómo manejar tags de release? (ej: v1.2.0 → pro)
- [ ] ¿Indexamos por branch, por tag, o por commit específico?

### Entidades del Grafo
- [ ] ¿Los nodos del grafo deben tener estado independiente del documento?
- [ ] ¿Cómo manejar entidades que aparecen en múltiples documentos con diferentes estados?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [Content Lifecycle Management](https://en.wikipedia.org/wiki/Content_lifecycle_management)
- [Feature Flags & Progressive Delivery](https://launchdarkly.com/blog/what-are-feature-flags/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [State Machines for Content](https://xstate.js.org/docs/)
