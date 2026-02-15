# language: es
Característica: Análisis de impacto por grafo
  Como agente de IA
  Quiero conocer el impacto de cambiar un nodo
  Para saber qué artefactos se ven afectados antes de modificar una spec

  Antecedentes:
    Dado un índice con los siguientes nodos y edges:
      | from_node          | edge_type       | to_node              |
      | BR:BR-DOCUMENT-001 | ENTITY_RULE     | Entity:KDDDocument   |
      | UC:UC-001          | UC_APPLIES_RULE | BR:BR-DOCUMENT-001   |
      | UC:UC-001          | UC_EXECUTES_CMD | CMD:CMD-001          |
      | CMD:CMD-001        | WIKI_LINK       | Entity:KDDDocument   |

  Escenario: SCN-RetrieveImpact-001 — Impacto directo e indirecto
    Cuando consulto impacto de "Entity:KDDDocument" con profundidad 3
    Entonces los nodos directamente afectados son:
      | node_id            | edge_type     |
      | BR:BR-DOCUMENT-001 | ENTITY_RULE   |
      | CMD:CMD-001        | WIKI_LINK     |
    Y los nodos transitivamente afectados son:
      | node_id   | path                                              |
      | UC:UC-001 | Entity:KDDDocument → BR:BR-DOCUMENT-001 → UC:UC-001 |
    Y la respuesta completa en menos de 500ms

  Escenario: SCN-RetrieveImpact-002 — Nodo hoja sin dependientes
    Cuando consulto impacto de "UC:UC-001" con profundidad 3
    Entonces los nodos directamente afectados están vacíos
    Y los nodos transitivamente afectados están vacíos

  Escenario: SCN-RetrieveImpact-003 — Nodo inexistente
    Cuando consulto impacto de "Entity:NoExiste" con profundidad 2
    Entonces recibo error "NODE_NOT_FOUND"
