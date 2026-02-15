# language: es
Característica: Funcionamiento offline-first
  Como desarrollador
  Quiero que la indexación y el retrieval funcionen sin conexión
  Para no depender de un servidor para trabajar con mis specs

  Escenario: SCN-OfflineFirst-001 — Indexación L1 sin conexión
    Dado que no tengo conexión a internet
    Y no tengo modelo de embeddings local
    Cuando ejecuto "kb index specs/01-domain/entities/Pedido.md"
    Entonces se genera un nodo "Entity:Pedido" con sus edges
    Y el nivel de indexación es "L1"
    Y no se generan embeddings
    Y no se envía ninguna petición a servicios externos

  Escenario: SCN-OfflineFirst-002 — Indexación L2 sin conexión
    Dado que no tengo conexión a internet
    Pero tengo el modelo "nomic-embed-text-v1.5" descargado localmente
    Cuando ejecuto "kb index specs/01-domain/entities/Pedido.md"
    Entonces se genera un nodo "Entity:Pedido" con edges y embeddings
    Y el nivel de indexación es "L2"
    Y no se envía ninguna petición a servicios externos

  Escenario: SCN-OfflineFirst-003 — Retrieval local sin conexión
    Dado un índice L2 existente
    Y que no tengo conexión a internet
    Cuando busco "pedido de compra" con strategy "hybrid"
    Entonces recibo resultados de la búsqueda
    Y no se envía ninguna petición a servicios externos

  Escenario: SCN-OfflineFirst-004 — Push de artefactos no transmite specs
    Dado un índice L2 existente
    Cuando ejecuto "kb sync push"
    Entonces se transmiten los artefactos de ".kdd-index/"
    Y no se transmite ningún fichero de "/specs"
    Y los artefactos no contienen el contenido Markdown original

  Escenario: SCN-OfflineFirst-005 — L3 falla gracefully sin conexión
    Dado que no tengo conexión a internet
    Cuando ejecuto "kb enrich Entity:Pedido"
    Entonces recibo error "API_KEY_MISSING" o "AGENT_TIMEOUT"
    Y el índice existente no se modifica
