# DC-006: Diseño de API

---
id: DC-006
status: open
priority: media
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El backend expone APIs para dos procesos principales: indexación e inferencia. Además, se necesitan APIs para gestión (curación, administración). El diseño debe considerar diferentes clientes: MCP, UI de curación, integraciones externas.

### Requisitos ya definidos

- **Separación**: Indexación e Inferencia son procesos distintos
- **Clientes**: MCP (principal), UI de curación, APIs directas
- **Seguridad**: RBAC integrado en todas las APIs
- **Latencia**: Muy baja para inferencia

### Contexto Técnico

- Backend: Python (probablemente FastAPI)
- Autenticación: OAuth2/OIDC (ver DC-005)
- Operaciones async para indexación (puede ser larga)

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: API de Inferencia (query, retrieval)
- [ ] RF2: API de Indexación (ingest, reindex, delete)
- [ ] RF3: API de Curación (validar entidades, aprobar, rechazar)
- [ ] RF4: API de Administración (configuración, métricas)
- [ ] RF5: Operaciones async con status tracking
- [ ] RF6: Versionado de API

### 2.2 Requisitos No Funcionales

- [ ] RNF1: Latencia de inferencia < X ms
- [ ] RNF2: Documentación OpenAPI automática
- [ ] RNF3: Rate limiting por cliente
- [ ] RNF4: Observabilidad (métricas, traces)

### 2.3 Restricciones

- Compatible con protocolo MCP
- Autenticación obligatoria en todos los endpoints
- Respuestas deben incluir trazabilidad (source documents)

## 3. Opciones Consideradas

### Opción A: REST API Monolítica

**Descripción**: Una única API REST que expone todos los endpoints.

```
/api/v1/
├── /query              POST  (inferencia)
├── /documents          CRUD  (indexación)
├── /entities           CRUD  (curación)
├── /graphs             GET   (exploración)
└── /admin/             *     (administración)
```

**Pros**:
- Simple de desarrollar y desplegar
- Un único punto de entrada
- Fácil de documentar

**Contras**:
- Puede crecer demasiado
- Difícil escalar componentes independientemente
- Un fallo afecta todo

**Esfuerzo estimado**: Bajo

---

### Opción B: APIs Separadas (Indexación / Inferencia / Admin)

**Descripción**: Múltiples APIs/servicios especializados.

```
Indexing API:     /indexing/v1/documents, /indexing/v1/jobs
Inference API:    /inference/v1/query, /inference/v1/search
Curation API:     /curation/v1/entities, /curation/v1/validations
Admin API:        /admin/v1/config, /admin/v1/metrics
```

**Pros**:
- Separación clara de concerns
- Escalado independiente
- Equipos pueden trabajar en paralelo

**Contras**:
- Más complejo de orquestar
- Múltiples deployments
- Puede requerir API Gateway

**Esfuerzo estimado**: Alto

---

### Opción C: REST + GraphQL para Consultas

**Descripción**: REST para operaciones CRUD, GraphQL para queries complejas de inferencia.

```
REST:    /api/v1/documents, /api/v1/entities (CRUD)
GraphQL: /graphql (queries flexibles, exploración de grafo)
```

**Pros**:
- GraphQL ideal para consultas complejas del grafo
- Cliente puede pedir exactamente lo que necesita
- Reduce over-fetching

**Contras**:
- Dos paradigmas que mantener
- GraphQL tiene curva de aprendizaje
- Caching más complejo en GraphQL

**Esfuerzo estimado**: Alto

---

### Opción D: REST con Módulos Internos

**Descripción**: API REST única pero con routers/módulos internos bien separados.

```python
# main.py
app = FastAPI()
app.include_router(inference_router, prefix="/api/v1/inference")
app.include_router(indexing_router, prefix="/api/v1/indexing")
app.include_router(curation_router, prefix="/api/v1/curation")
app.include_router(admin_router, prefix="/api/v1/admin")
```

**Pros**:
- Un deployment, código modular
- Fácil evolucionar a microservicios si se necesita
- Documentación unificada

**Contras**:
- Aún comparte recursos
- Menos aislamiento que servicios separados

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | Monolítica | Separadas | REST+GraphQL | Modular |
|----------|------|------------|-----------|--------------|---------|
| Simplicidad inicial | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| Escalabilidad | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Mantenibilidad | 3 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Flexibilidad queries | 2 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Complejidad ops | 2 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Total ponderado** | | 25 | 22 | 25 | 29 |

## 5. Preguntas Abiertas

- [ ] ¿El MCP tiene requisitos específicos de protocolo?
- [ ] ¿Se necesitan WebSockets para updates en tiempo real?
- [ ] ¿Cuál es el volumen esperado de requests por endpoint?
- [ ] ¿Se requiere versionado semántico o por fecha?
- [ ] ¿Habrá SDK/cliente generado automáticamente?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [REST API Design Guidelines](https://restfulapi.net/)
- [GraphQL vs REST](https://www.apollographql.com/blog/graphql/basics/graphql-vs-rest/)
- [MCP Protocol](https://modelcontextprotocol.io/)
