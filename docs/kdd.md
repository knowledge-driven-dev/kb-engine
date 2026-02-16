# KDD Model Reference (Agent Context)

> **Purpose**: Minimal context for subagents working with KDD specifications.
> For human documentation, see `/kdd/docs/introducción.md`.

## Core Principle

**Specification > Code**: Docs are the source of truth; code is derived/regenerable.

---

## Folder Structure (`/specs`)

```
/specs
├── 00-requirements/       # INPUT - Business context (alimenta al diseño)
│   ├── PRD.md
│   ├── objectives/        # OBJ-NNN-*.md (User Stories alto nivel)
│   ├── value-units/       # UV-NNN-*.md (Unidades de Valor)
│   ├── releases/          # REL-NNN-*.md (Release plans)
│   └── decisions/         # ADR-NNN-*.md
├── 01-domain/             # BASE - Domain model (fundamento)
│   ├── entities/          # Entity.md (PascalCase)
│   ├── events/            # EVT-Entity-Action.md
│   └── rules/             # BR-*-NNN.md (Business Rules)
├── 02-behavior/           # ORCHESTRATION - How the system behaves
│   ├── commands/          # CMD-NNN-*.md
│   ├── queries/           # QRY-NNN-*.md
│   ├── processes/         # PROC-NNN-*.md
│   ├── policies/          # BP-*-NNN.md, XP-*-NNN.md (Business & Cross Policies)
│   └── use-cases/         # UC-NNN-*.md
├── 03-experience/         # PRESENTATION - How users see it
│   └── views/             # UI-*.md
├── 04-verification/       # VALIDATION - How we test it
│   ├── criteria/          # REQ-NNN-*.md
│   └── examples/          # *.feature (BDD)
└── 05-architecture/       # TECHNICAL - Infrastructure decisions
```

### Multi-Domain Structure (Optional)

For large applications with multiple bounded contexts, use the multi-domain structure:

```
/specs
├── _shared/                  # Cross-domain policies and glossary
│   ├── policies/             # XP-* policies
│   └── domain-map.md         # Domain dependency visualization
├── domains/
│   ├── core/                 # Foundational domain
│   │   ├── _manifest.yaml    # Domain metadata and dependencies
│   │   ├── 01-domain/
│   │   └── ...
│   ├── auth/                 # Authentication domain
│   └── sessions/             # Sessions domain
└── _index.json               # Global index
```

**Cross-domain references**: Use `[[domain::Entity]]` syntax (e.g., `[[core::Usuario]]`).

**See**: `/kdd/docs/multi-domain.md` for complete documentation.

---

## Artifact Types & IDs

| Type            | Prefix | ID Pattern              | File Pattern               | Location                       |
| --------------- | ------ | ----------------------- | -------------------------- | ------------------------------ |
| Objective       | OBJ    | `OBJ-NNN`               | `OBJ-NNN-{Name}.md`        | `00-requirements/objectives/`  |
| Value Unit      | UV     | `UV-NNN`                | `UV-NNN-{Name}.md`         | `00-requirements/value-units/` |
| Release         | REL    | `REL-NNN`               | `REL-NNN-{Name}.md`        | `00-requirements/releases/`    |
| ADR             | ADR    | `ADR-NNNN`              | `ADR-NNNN-{Title}.md`      | `00-requirements/decisions/`   |
| Entity          | -      | -                       | `PascalCase.md`            | `01-domain/entities/`          |
| Event           | EVT    | `EVT-{Entity}-{Action}` | `EVT-{Entity}-{Action}.md` | `01-domain/events/`            |
| Business Rule   | BR     | `BR-{ENTITY}-NNN`       | `BR-{ENTITY}-NNN.md`       | `01-domain/rules/`             |
| Business Policy | BP     | `BP-{TOPIC}-NNN`        | `BP-{TOPIC}-NNN.md`        | `02-behavior/policies/`        |
| Command         | CMD    | `CMD-NNN`               | `CMD-NNN-{Name}.md`        | `02-behavior/commands/`        |
| Query           | QRY    | `QRY-NNN`               | `QRY-NNN-{Name}.md`        | `02-behavior/queries/`         |
| Process         | PROC   | `PROC-NNN`              | `PROC-NNN-{Name}.md`       | `02-behavior/processes/`       |
| Use Case        | UC     | `UC-NNN`                | `UC-NNN-{Name}.md`         | `02-behavior/use-cases/`       |
| Cross-Policy    | XP     | `XP-{TOPIC}-NNN`        | `XP-{TOPIC}-NNN.md`        | `02-behavior/policies/`        |
| UI View         | UI     | -                       | `UI-{Name}.md`             | `03-experience/views/`         |
| Requirement     | REQ    | `REQ-NNN`               | `REQ-NNN-{Name}.md`        | `04-verification/criteria/`    |

---

## Layer Dependencies

```
┌───────────────────────────────────────────────────────────────┐
│  00-requirements   (PRD, objectives, ADRs)                    │
│  INPUT: Alimenta al diseño. Puede mencionar conceptos de      │
│  dominio para dar contexto. No es parte del flujo de capas.   │
└───────────────────────────────────────────────────────────────┘
                              ↓ alimenta
┌───────────────────────────────────────────────────────────────┐
│  04-verification   (tests, criteria)                          │
│      ↓ references                                             │
├───────────────────────────────────────────────────────────────┤
│  03-experience     (views)                                    │
│      ↓ references                                             │
├───────────────────────────────────────────────────────────────┤
│  02-behavior       (UC, CMD, QRY, XP)                         │
│      ↓ references                                             │
├───────────────────────────────────────────────────────────────┤
│  01-domain         (entities, rules)   ← BASE                 │
└───────────────────────────────────────────────────────────────┘
```

**Rule**: Higher layers (04→03→02→01) CAN reference lower layers. Lower layers SHOULD NOT reference higher layers.

> **00-requirements** está fuera del flujo de dependencias. Es el input que alimenta el diseño, por lo que naturalmente puede mencionar conceptos de dominio sin violar la regla de capas.

---

## Status Lifecycle

Todos los artefactos usan el mismo ciclo:

```
draft → review → approved → deprecated
```

| Status | Significado |
|--------|-------------|
| `draft` | Work in progress, no es fuente de verdad |
| `review` | Pendiente de aprobación |
| `approved` | Fuente de verdad oficial |
| `deprecated` | Obsoleto, debe linkar al reemplazo |

> **Nota**: No usar `proposed`. Usar `review` para artefactos pendientes de aprobación.

---

## Language Policy

| Aspecto                       | Idioma            | Ejemplo                                |
| ----------------------------- | ----------------- | -------------------------------------- |
| Secciones de contenido        | Español           | `## Declaración`, `## Flujo Principal` |
| Nombres de secciones técnicas | Inglés (opcional) | `## Purpose`, `## Input`               |
| Código y ejemplos             | Inglés            | `function createChallenge()`           |
| IDs y prefijos                | Inglés            | `CMD-009`, `BR-SESION-001`             |
| Contenido narrativo           | Español           | "El Usuario crea un Reto..."           |

> **Consistencia**: Dentro de un mismo archivo, mantener el idioma elegido para las secciones.

---

## Front-Matter by Type

> **Nota**: El atributo `kind` indica el tipo de artefacto KDD. Los `tags` son opcionales y se usan para categorización adicional (no para indicar el tipo).

### Entity

```yaml
---
id: "{EntityName}"       # Optional, defaults to filename
kind: entity             # Required
aliases: []              # Optional alternative names
status: draft            # draft|review|approved|deprecated
---
```

### Event (EVT)

```yaml
---
id: EVT-{Entity}-{Action}  # Required, must match filename
kind: event                # Required
title: "{Entity} {Action}" # Required
status: draft
---
```

### Business Rule (BR)

```yaml
---
id: BR-{ENTITY}-NNN      # Required, e.g., BR-SESION-001
kind: business-rule      # Required
title: RuleName          # Required
entity: EntityName       # Required: entidad principal afectada
category: validation     # validation|state|limit|security
severity: medium         # low|medium|high|critical
status: draft
---
```

### Business Policy (BP)

```yaml
---
id: BP-{TOPIC}-NNN       # Required, e.g., BP-CREDITO-001
kind: business-policy    # Required
title: PolicyName        # Required
entity: EntityName       # Optional: entidad principal afectada
category: business       # business|compliance|limit
severity: medium         # low|medium|high|critical
status: draft
---
```

### Cross-Policy (XP)

```yaml
---
id: XP-{TOPIC}-NNN       # Required, e.g., XP-CREDITOS-001
kind: cross-policy       # Required
title: PolicyName        # Required
status: draft
---
```

### Command (CMD)

```yaml
---
id: CMD-NNN              # Required, pattern: ^CMD-\d{3}$
kind: command            # Required
title: CommandName       # Required
status: draft
billable: false          # Optional: if true, applies XP-CREDITOS-001
credit-cost: 0           # Optional: credits consumed (requires billable: true)
tags: [core, destructive] # Optional: categorization tags
---
```

### Query (QRY)

```yaml
---
id: QRY-NNN              # Required, pattern: ^QRY-\d{3}$
kind: query              # Required
title: QueryName         # Required
status: draft
---
```

### Use Case (UC)

```yaml
---
id: UC-NNN               # Required, pattern: ^UC-\d{3}$
kind: use-case           # Required
title: UseCaseName       # Required
version: 1               # Number, default: 1
status: draft            # draft|review|approved|deprecated
actor: ActorName         # Required
---
```

### UI View

```yaml
---
id: UI-{Name}            # Optional, defaults to filename
kind: ui-view            # Required
title: ViewName          # Required
status: draft
links:
  use-cases: []          # UCs this view triggers
  components: []         # UI components used
---
```

### UI Component

```yaml
---
id: UI-{Name}            # Optional, defaults to filename
kind: ui-component       # Required
title: ComponentName     # Required
status: draft
links:
  entities: []           # Domain entities used
  use-cases: []          # UCs this component supports
---
```

### Requirement (REQ)

```yaml
---
id: REQ-NNN              # Required, pattern: ^REQ-\d{3}$
kind: requirement        # Required
title: RequirementName   # Required
status: draft
priority: medium         # low|medium|high|critical
source: PRD              # Where this requirement comes from
---
```

### Objective (OBJ)

```yaml
---
id: OBJ-NNN              # Required, pattern: ^OBJ-\d{3}$
kind: objective          # Required
title: ObjectiveName     # Required
actor: ActorName         # Required
status: draft
---
```

### Process (PROC)

```yaml
---
id: PROC-NNN             # Required, pattern: ^PROC-\d{3}$
kind: process            # Required
title: ProcessName       # Required
status: draft
---
```

---

## Required Sections by Type

### Entity

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Descripción` | Sí | Qué es y para qué sirve |
| `## Atributos` | Sí | Tabla con campos |
| `## Ciclo de Vida` | No | Diagrama mermaid stateDiagram |
| `## Relaciones` | No | Relaciones con otras entidades |
| `## Invariantes` | No | Restricciones que siempre deben cumplirse |

### Command

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Purpose` | Sí | Qué hace el comando |
| `## Input` | Sí | Tabla: Parameter, Type, Required, Validation |
| `## Preconditions` | Sí | Lista de condiciones previas |
| `## Postconditions` | Sí | Estado después de ejecutar |
| `## Possible Errors` | Sí | Tabla: Code, Condition, Message |

**Columnas requeridas para Input:**
| Parameter | Type | Required | Validation |
|-----------|------|----------|------------|

**Columnas requeridas para Errors:**
| Code | Condition | Message |
|------|-----------|---------|

### Query

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Purpose` | Sí | Qué datos devuelve |
| `## Input` | Sí | Tabla con parámetros |
| `## Output` | Sí | Estructura de respuesta |
| `## Possible Errors` | Sí | Tabla de errores |

### Use Case

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Descripción` | Sí | Resumen del caso de uso |
| `## Actores` | Sí | Quiénes participan |
| `## Precondiciones` | Sí | Estado inicial requerido |
| `## Flujo Principal` | Sí | Pasos del camino feliz |
| `## Flujos Alternativos` | No | Variaciones válidas |
| `## Excepciones` | No | Qué pasa cuando algo falla |
| `## Postcondiciones` | Sí | Estado final |
| `## Reglas Aplicadas` | No | BR-*, BP-*, XP-* que se validan |
| `## Comandos Ejecutados` | No | CMD-* que se invocan |

### Business Rule (BR/BP)

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Declaración` | Sí | Descripción clara con wiki-links |
| `## Por qué existe` | Sí | Justificación de negocio |
| `## Cuándo aplica` | Sí | Condiciones de activación |
| `## Qué pasa si se incumple` | Sí | Consecuencias |
| `## Parámetros` | Solo BP | Valores configurables |
| `## Formalización` | No | Patrón EARS |
| `## Ejemplos` | Sí | Casos válidos e inválidos |

### Cross-Policy (XP)

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Propósito` | Sí | Por qué es transversal |
| `## Declaración` | Sí | Qué hace la política |
| `## Formalización EARS` | Sí | BEFORE/AFTER pattern |
| `## Ejemplos` | Sí | Verificación exitosa/fallida |
| `## Comportamiento Estándar` | Sí | BEFORE, AFTER, Rechazo, Rollback |
| `## Implementación` | No | Código de referencia |

### UI View

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Descripción` | Sí | Propósito de la vista |
| `## Layout` | Sí | Wireframe ASCII o imagen |
| `## Componentes Utilizados` | Sí | Lista de componentes |
| `## Estados` | Sí* | loading, empty, error, success |
| `## Comportamiento` | Sí | Interacciones y navegación |

> *Estados: Incluir solo los **aplicables** a la vista. Una vista sin datos puede omitir `empty`. Una vista estática puede omitir `loading`.

### Requirement (REQ)

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Descripción` | Sí | Qué debe cumplirse |
| `## Criterios de Aceptación` | Sí | Lista de condiciones verificables |
| `## Trazabilidad` | Sí | Links a UC-*, BR-*, CMD-* que implementan |

### Objective (OBJ)

| Sección | Requerida | Descripción |
|---------|-----------|-------------|
| `## Actor` | Sí | Quién tiene este objetivo |
| `## Objetivo` | Sí | "Como X, quiero Y, para Z" |
| `## Criterios de éxito` | Sí | Cómo sabe el usuario que lo logró |
| `## Casos de uso relacionados` | No | Links a UC-* |

---

## Wiki-Link Syntax

```markdown
[[Reto]]                       # Link to entity
[[Sesión|sesiones]]            # Link with display alias
[[BR-RETO-001]]                # Link to rule
[[CMD-001-CreateChallenge]]    # Link to command
[[UC-001-CrearReto]]           # Link to use case
[[XP-CREDITOS-001]]            # Link to cross-policy
```

---

## Naming Conventions

### Domain Entities in Text

- **Always capitalize** domain entities: `El Usuario crea un Reto`
- First mention → wiki-link: `[[Reto]]`
- Plurals with alias: `[[Sesión|Sesiones]]`
- In code → lowercase: `const reto = await createReto()`

### File Names

- Entities: `PascalCase.md` (e.g., `Persona Sintética.md`)
- Everything else: Use prefix pattern (e.g., `CMD-001-CreateChallenge.md`)

---

## Templates

All templates are in `/kdd/templates/`:

| Template | For |
|----------|-----|
| `entity.template.md` | Domain entities |
| `event.template.md` | Domain events |
| `rule.template.md` | Business rules (BR) |
| `cross-policy.template.md` | Cross-cutting policies (XP) |
| `command.template.md` | Commands (CQRS write) |
| `query.template.md` | Queries (CQRS read) |
| `process.template.md` | Business processes |
| `use-case.template.md` | Use cases |
| `ui-view.template.md` | UI views/pages |
| `ui-flow.template.md` | UI navigation flows |
| `ui-component.template.md` | Reusable UI components |
| `prd.template.md` | Product Requirements |
| `adr.template.md` | Architecture Decisions |
| `requirement.template.md` | Functional requirements |

---

## Validation

```bash
bun run validate:specs   # Validate all specs
```

Checks: front-matter schema, broken links, required sections.

---

## Key References

- Human docs: `/kdd/docs/introducción.md`
- Writing conventions: `/kdd/docs/convenciones-escritura.md`
- Validation details: `/kdd/docs/validacion-especificaciones.md`
- Multi-domain support: `/kdd/docs/multi-domain.md`
