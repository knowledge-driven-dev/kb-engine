# DC-001: Modelo de Seguridad

---
id: DC-001
status: open
priority: alta
created: 2025-01-16
updated: 2025-01-16
owner: TBD
adrs: []
---

## 1. Contexto

El sistema de retrieval maneja documentación sensible de proyectos de desarrollo. Es crítico implementar un modelo de seguridad **by design** que controle el acceso a:

- Documentos (fuente original)
- Chunks (fragmentos indexados)
- Embeddings (vectores en BBDD vectorial)
- Nodos y relaciones (grafo de conocimiento)

El control de acceso debe aplicarse a nivel de **documento** y **proyecto/dominio**, con roles provenientes de un **IdP externo**.

### Contexto Técnico

- **3 bases de datos**: PostgreSQL (trazabilidad), Vector DB, Graph DB
- **Tenancy**: Un despliegue por dominio/proyecto (aislamiento total)
- **Roles**: Externos (IdP)
- **Futuro**: Rol de Knowledge Manager/Owner con permisos especiales

## 2. Requisitos y Restricciones

### 2.1 Requisitos Funcionales

- [ ] RF1: Control de acceso a nivel de documento
- [ ] RF2: Control de acceso a nivel de proyecto/dominio
- [ ] RF3: Filtrado de resultados de búsqueda según permisos del usuario
- [ ] RF4: Propagación de permisos: documento → chunks → embeddings → nodos
- [ ] RF5: Integración con IdP externo para obtención de roles
- [ ] RF6: Soporte para rol Knowledge Manager con permisos de curación

### 2.2 Requisitos No Funcionales

- [ ] RNF1: La verificación de permisos no debe impactar significativamente la latencia de retrieval
- [ ] RNF2: El modelo debe ser auditable (quién accedió a qué, cuándo)
- [ ] RNF3: Debe soportar cambios de permisos sin reindexación

### 2.3 Restricciones

- Los roles vienen de un IdP externo (no se gestionan internamente)
- Cada despliegue es aislado por proyecto (no hay multi-tenancy cruzado)
- Debe funcionar con cualquier combinación de Vector DB + Graph DB soportada

## 3. Opciones Consideradas

### Opción A: RBAC Puro (Role-Based Access Control)

**Descripción**: Control de acceso basado únicamente en roles. Cada documento/proyecto tiene roles asignados (viewer, editor, admin). El usuario hereda permisos de sus roles.

```
Usuario → tiene → Roles → acceden a → Recursos
```

**Pros**:
- Simple de implementar y entender
- Mapeo directo con roles del IdP
- Bajo overhead en verificación

**Contras**:
- Poco flexible para permisos granulares
- No soporta bien reglas contextuales (ej: "solo documentos creados por mí")
- Explosión de roles si se necesita granularidad

**Esfuerzo estimado**: Bajo

---

### Opción B: ABAC (Attribute-Based Access Control)

**Descripción**: Control de acceso basado en atributos del usuario, recurso y contexto. Las políticas se definen como reglas que evalúan atributos.

```
Política: ALLOW si (user.department == resource.domain AND user.role IN ['developer', 'architect'])
```

**Pros**:
- Muy flexible y expresivo
- Soporta reglas contextuales complejas
- No hay explosión de roles

**Contras**:
- Más complejo de implementar
- Evaluación de políticas puede impactar latencia
- Más difícil de auditar y depurar

**Esfuerzo estimado**: Alto

---

### Opción C: RBAC + Filtros por Dominio (Híbrido Simple)

**Descripción**: RBAC para permisos base + filtrado automático por dominio/proyecto. El dominio se extrae del token del IdP y se aplica como filtro implícito en todas las consultas.

```
Usuario → tiene → Roles (del IdP)
       → pertenece a → Dominio (claim del token)

Consulta = query + filtro_dominio + filtro_rol
```

**Pros**:
- Equilibrio entre simplicidad y flexibilidad
- El filtro por dominio es implícito (seguro por defecto)
- Compatible con el modelo de tenancy aislado

**Contras**:
- Menos flexible que ABAC puro
- Requiere que el IdP incluya el dominio en el token

**Esfuerzo estimado**: Medio

---

### Opción D: RBAC con Herencia y Scopes

**Descripción**: RBAC extendido donde los roles tienen scopes (documento, proyecto, global) y hay herencia de permisos.

```
Rol: project-editor
Scope: proyecto-X
Permisos: [read, write, validate]

Herencia: proyecto → documentos → chunks → nodos
```

**Pros**:
- Modelo mental claro (roles con alcance)
- Soporta el rol Knowledge Manager naturalmente
- Herencia reduce duplicación de permisos

**Contras**:
- Más complejo que RBAC puro
- Requiere diseñar jerarquía de scopes

**Esfuerzo estimado**: Medio

## 4. Análisis Comparativo

| Criterio | Peso | RBAC Puro | ABAC | Híbrido Simple | RBAC + Scopes |
|----------|------|-----------|------|----------------|---------------|
| Simplicidad de implementación | 3 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| Flexibilidad | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Impacto en latencia | 3 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| Soporte Knowledge Manager | 2 | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Auditabilidad | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Compatibilidad IdP | 2 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Total ponderado** | | 36 | 26 | 37 | 36 |

## 5. Preguntas Abiertas

- [ ] ¿El IdP puede incluir claims personalizados (dominio, proyecto)?
- [ ] ¿Se necesitan permisos a nivel de documento individual o solo proyecto?
- [ ] ¿El Knowledge Manager tiene permisos sobre todo el proyecto o subconjuntos?
- [ ] ¿Se requiere auditoría de accesos (compliance)?
- [ ] ¿Los permisos deben poder cambiar dinámicamente sin reiniciar?

## 6. Decisión

> **Estado**: Pendiente

**Opción seleccionada**: -

**Justificación**: -

**ADRs generados**: -

## 7. Referencias

- [NIST ABAC Guide](https://csrc.nist.gov/publications/detail/sp/800-162/final)
- [RBAC vs ABAC](https://www.okta.com/identity-101/role-based-access-control-vs-attribute-based-access-control/)
- [Casbin](https://casbin.org/) - Librería de autorización multi-modelo
- [OPA (Open Policy Agent)](https://www.openpolicyagent.org/) - Motor de políticas
