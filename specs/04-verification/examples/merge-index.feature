# language: es
Característica: Merge de índices de múltiples desarrolladores
  Como servidor compartido
  Quiero mergear índices de varios desarrolladores
  Para ofrecer un grafo unificado al API de retrieval

  Antecedentes:
    Dado que Dev A y Dev B tienen índices con embedding_model "nomic-embed-text-v1.5"
    Y ambos índices tienen version "1.0.0"

  Escenario: SCN-MergeIndex-001 — Merge sin conflictos
    Dado que Dev A indexó "Entity:Pedido" y "BR:BR-DOCUMENT-001"
    Y Dev B indexó "Entity:Usuario" y "CMD:CMD-001"
    Cuando ejecuto merge de los dos índices
    Entonces el índice mergeado tiene 4 nodos
    Y tiene 0 conflictos resueltos
    Y se emite "EVT-Index-MergeCompleted"

  Escenario: SCN-MergeIndex-002 — Merge con conflicto last-write-wins
    Dado que Dev A indexó "Entity:Pedido" con hash "abc123" a las 10:00
    Y Dev B indexó "Entity:Pedido" con hash "xyz999" a las 10:15
    Cuando ejecuto merge de los dos índices
    Entonces el índice mergeado tiene el nodo "Entity:Pedido" con hash "xyz999"
    Y tiene 1 conflicto resuelto
    Y los embeddings de "Entity:Pedido" son los de Dev B

  Escenario: SCN-MergeIndex-003 — Merge con eliminación (delete-wins)
    Dado que Dev A eliminó "Entity:Pedido" de su índice
    Y Dev B tiene "Entity:Pedido" sin cambios
    Cuando ejecuto merge de los dos índices
    Entonces el nodo "Entity:Pedido" no existe en el índice mergeado
    Y los edges de "Entity:Pedido" han sido eliminados

  Escenario: SCN-MergeIndex-004 — Merge incompatible rechazado
    Dado que Dev A tiene embedding_model "nomic-embed-text-v1.5"
    Y Dev B tiene embedding_model "bge-small-en-v1.5"
    Cuando intento merge de los dos índices
    Entonces recibo error "INCOMPATIBLE_EMBEDDING_MODEL"
    Y no se genera índice mergeado
