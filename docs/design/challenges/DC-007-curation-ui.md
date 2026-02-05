# DC-007: UI de Curación

---
id: DC-007
status: open
priority: baja
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

Se requiere una interfaz de usuario para que humanos validen y curen las entidades y relaciones extraídas automáticamente. Esta UI será usada principalmente por el futuro rol de Knowledge Manager/Owner.

### Requisitos ya definidos

- **Validación humana**: Obligatoria antes de aprobar entidades
- **Gestión de entidades y grafos**: Ver, editar, aprobar, rechazar
- **Futuro rol**: Knowledge Manager/Owner con herramientas especializadas

### Contexto Técnico

- Backend: Python con API REST (ver DC-006)
- Operaciones: CRUD de entidades, validación de relaciones, visualización de grafo
- Usuarios: Técnicos/semi-técnicos (Knowledge Managers)

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Listar entidades pendientes de validación
- [ ] RF2: Ver detalle de entidad con su contexto (documento origen, chunk)
- [ ] RF3: Aprobar/rechazar entidades
- [ ] RF4: Editar entidades (nombre, tipo, atributos)
- [ ] RF5: Gestionar relaciones entre entidades
- [ ] RF6: Visualizar grafo de conocimiento
- [ ] RF7: Filtrar por tipo, estado, dominio, fecha

### 2.2 Requisitos No Funcionales

- [ ] RNF1: UI responsiva
- [ ] RNF2: Accesible (WCAG 2.1 AA)
- [ ] RNF3: Tiempo de carga < 2s

### 2.3 Restricciones

- Autenticación mediante IdP externo (SSO)
- Debe mostrar trazabilidad (origen de cada entidad)
- Prioridad baja (puede empezar después del backend)

## 3. Opciones Consideradas

### Opción A: SPA con React/Vue

**Descripción**: Single Page Application moderna con framework JS.

```
Frontend (React/Vue) ←→ Backend API (FastAPI)
```

**Pros**:
- Experiencia de usuario fluida
- Ecosistema maduro de componentes
- Fácil integración con librerías de grafos (D3, Cytoscape)

**Contras**:
- Requiere expertise frontend
- Build y deploy separado
- Más complejo de mantener

**Esfuerzo estimado**: Alto

---

### Opción B: Server-Side Rendering (HTMX + Jinja)

**Descripción**: Renderizado en servidor con interactividad ligera via HTMX.

```python
@app.get("/entities")
def list_entities():
    entities = get_pending_entities()
    return templates.TemplateResponse("entities.html", {"entities": entities})
```

**Pros**:
- Stack unificado (Python)
- Más simple de desarrollar
- Menos JS que mantener
- Buen rendimiento para operaciones CRUD

**Contras**:
- UX menos fluida que SPA
- Visualización de grafo más limitada
- Menos componentes disponibles

**Esfuerzo estimado**: Medio

---

### Opción C: Low-Code (Retool, Appsmith)

**Descripción**: Usar plataforma low-code que consume la API del backend.

**Pros**:
- Desarrollo muy rápido
- No requiere frontend developers
- Ideal para herramientas internas

**Contras**:
- Dependencia de plataforma externa
- Menos customizable
- Puede tener costos de licencia
- Visualización de grafo limitada

**Esfuerzo estimado**: Bajo

---

### Opción D: Admin Framework (Django Admin style / FastAPI-Admin)

**Descripción**: Usar framework de admin que genera UI automáticamente desde modelos.

```python
from fastapi_admin import admin

@admin.register(Entity)
class EntityAdmin:
    list_display = ["name", "type", "status", "created_at"]
    list_filter = ["type", "status"]
    search_fields = ["name"]
```

**Pros**:
- Generación automática de CRUD
- Rápido de implementar
- Consistente con modelos de datos

**Contras**:
- Menos flexible para UX custom
- Visualización de grafo requiere extensión
- Puede no cubrir todos los flujos

**Esfuerzo estimado**: Bajo-Medio

## 4. Análisis Comparativo

| Criterio | Peso | SPA | SSR/HTMX | Low-Code | Admin Framework |
|----------|------|-----|----------|----------|-----------------|
| UX/Fluidez | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| Velocidad desarrollo | 3 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Visualización grafo | 2 | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ |
| Mantenibilidad | 2 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Independencia | 2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **Total ponderado** | | 26 | 26 | 25 | 28 |

## 5. Preguntas Abiertas

- [ ] ¿Cuántos Knowledge Managers usarán la UI concurrentemente?
- [ ] ¿Qué tan crítica es la visualización de grafo interactiva?
- [ ] ¿Se necesita edición masiva (bulk operations)?
- [ ] ¿Hay requisitos de branding/customización visual?
- [ ] ¿Se puede empezar simple e iterar?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [HTMX](https://htmx.org/)
- [FastAPI-Admin](https://github.com/fastapi-admin/fastapi-admin)
- [Retool](https://retool.com/)
- [Cytoscape.js](https://js.cytoscape.org/) - Visualización de grafos
- [React Flow](https://reactflow.dev/) - Diagramas interactivos
