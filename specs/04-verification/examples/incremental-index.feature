# language: es
Característica: Indexación incremental por git diff
  Como desarrollador
  Quiero que solo se re-indexen los documentos que cambié
  Para que la indexación sea rápida y no bloquee mi flujo de trabajo

  Antecedentes:
    Dado un índice existente con git_commit "abc123"
    Y el nivel de indexación es "L2"

  Escenario: SCN-IncrementalIndex-001 — Re-indexar documento modificado
    Dado que modifiqué "specs/01-domain/entities/Pedido.md" y hice commit
    Cuando ejecuto "kb index --incremental"
    Entonces se emite "EVT-KDDDocument-Stale" para "Entity:Pedido"
    Y se elimina el nodo anterior de "Entity:Pedido" con sus edges y embeddings
    Y se re-indexa "Pedido.md" generando nuevo nodo, edges y embeddings
    Y el manifest.git_commit se actualiza a HEAD
    Y el tiempo total es menor a 2 segundos

  Escenario: SCN-IncrementalIndex-002 — Indexar documento nuevo
    Dado que creé "specs/01-domain/entities/NuevaEntidad.md" y hice commit
    Cuando ejecuto "kb index --incremental"
    Entonces se emite "EVT-KDDDocument-Detected" para "NuevaEntidad"
    Y se genera un nodo "Entity:NuevaEntidad" con sus edges y embeddings
    Y las stats del manifest se incrementan

  Escenario: SCN-IncrementalIndex-003 — Eliminar documento
    Dado que eliminé "specs/01-domain/entities/Pedido.md" y hice commit
    Cuando ejecuto "kb index --incremental"
    Entonces se emite "EVT-KDDDocument-Deleted" para "Entity:Pedido"
    Y el nodo "Entity:Pedido" no existe en el índice
    Y los edges de "Entity:Pedido" han sido eliminados
    Y los embeddings de "Pedido" han sido eliminados

  Escenario: SCN-IncrementalIndex-004 — Sin cambios en specs
    Dado que el commit solo modificó ficheros fuera de "/specs"
    Cuando ejecuto "kb index --incremental"
    Entonces no se indexa ningún documento
    Y el manifest no se modifica

  Escenario: SCN-IncrementalIndex-005 — Primer indexación sin índice previo
    Dado que no existe ".kdd-index/"
    Cuando ejecuto "kb index --incremental"
    Entonces se ejecuta indexación completa de todos los ficheros en "/specs"
    Y se genera un manifest con git_commit de HEAD
