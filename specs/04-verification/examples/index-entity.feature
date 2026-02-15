# language: es
Característica: Indexación de una entidad KDD
  Como desarrollador
  Quiero indexar una entidad de dominio
  Para que el motor de retrieval pueda encontrarla por grafo y semántica

  Antecedentes:
    Dado un repositorio con estructura KDD en "/specs"
    Y el nivel de indexación es "L2"

  Escenario: SCN-IndexEntity-001 — Indexar entidad con ciclo de vida
    Dado un fichero "specs/01-domain/entities/Pedido.md" con:
      """
      ---
      kind: entity
      aliases: [Orden, Order]
      status: approved
      ---
      # Pedido
      ## Descripción
      Representa un pedido de compra realizado por un [[Usuario]].
      ## Atributos
      | Atributo | Tipo | Descripción |
      |----------|------|-------------|
      | id | uuid | Identificador único |
      | estado | enum | borrador, confirmado, enviado |
      ## Relaciones
      | Relación | Cardinalidad | Destino | Descripción |
      |----------|-------------|---------|-------------|
      | pertenece_a | N:1 | [[Usuario]] | El usuario que creó el pedido |
      """
    Cuando ejecuto "kb index specs/01-domain/entities/Pedido.md"
    Entonces se genera un nodo "Entity:Pedido" con kind "entity"
    Y el nodo tiene campo indexado "description" con "pedido de compra"
    Y se genera un edge "WIKI_LINK" de "Entity:Pedido" a "Entity:Usuario"
    Y se genera un edge "DOMAIN_RELATION" de "Entity:Pedido" a "Entity:Usuario" con metadata "cardinality=N:1"
    Y se genera un edge de negocio "pertenece_a" de "Entity:Pedido" a "Entity:Usuario"
    Y se generan embeddings para la sección "Descripción"
    Y no se generan embeddings para la sección "Atributos"
    Y el tiempo de indexación es menor a 2 segundos

  Escenario: SCN-IndexEntity-002 — Entidad sin front-matter se ignora
    Dado un fichero "specs/01-domain/entities/README.md" sin front-matter
    Cuando ejecuto "kb index specs/01-domain/entities/README.md"
    Entonces no se genera ningún nodo
    Y no se emite ningún evento

  Escenario: SCN-IndexEntity-003 — Entidad con kind incorrecto genera warning
    Dado un fichero "specs/02-behavior/MiEntidad.md" con kind "entity"
    Cuando ejecuto "kb index specs/02-behavior/MiEntidad.md"
    Entonces se genera un nodo "Entity:MiEntidad" con kind "entity"
    Y se registra un warning "entity found outside expected path"
