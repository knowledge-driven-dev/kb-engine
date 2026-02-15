# language: es
Característica: Soporte multi-domain con referencias cruzadas
  Como desarrollador de un proyecto con múltiples bounded contexts
  Quiero indexar specs con referencias cross-domain
  Para que el grafo de conocimiento refleje las dependencias entre dominios

  Antecedentes:
    Dado un repositorio con estructura multi-domain:
      | dominio  | ruta                       |
      | core     | specs/domains/core/        |
      | auth     | specs/domains/auth/        |
      | sessions | specs/domains/sessions/    |

  Escenario: SCN-MultiDomain-001 — Indexar referencia cross-domain
    Dado un fichero "specs/domains/auth/01-domain/entities/Token.md" que contiene "[[core::Usuario]]"
    Cuando indexo el fichero
    Entonces se genera un edge "CROSS_DOMAIN_REF" de "auth:Entity:Token" a "core:Entity:Usuario"
    Y el manifest.structure es "multi-domain"
    Y el manifest.domains contiene "auth" y "core"

  Escenario: SCN-MultiDomain-002 — Búsqueda híbrida cross-domain
    Dado un índice multi-domain con nodos en "core", "auth" y "sessions"
    Cuando busco "autenticación de usuario" con strategy "hybrid"
    Entonces los resultados pueden incluir nodos de "auth" y "core"
    Y el graph_expansion puede cruzar dominios

  Escenario: SCN-MultiDomain-003 — Merge de índices multi-domain
    Dado que Dev A indexó el dominio "core" y "auth"
    Y Dev B indexó el dominio "core" y "sessions"
    Cuando ejecuto merge
    Entonces el índice mergeado contiene nodos de los 3 dominios
    Y los edges CROSS_DOMAIN_REF se preservan
