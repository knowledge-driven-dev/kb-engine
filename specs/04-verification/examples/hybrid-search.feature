# language: es
Característica: Búsqueda híbrida para agentes
  Como agente de IA
  Quiero buscar contexto combinando semántica, grafo y lexical
  Para obtener los artefactos KDD más relevantes para mi tarea

  Antecedentes:
    Dado un índice L2 con entidades, reglas, commands y use cases indexados
    Y embeddings generados para las secciones embebibles

  Escenario: SCN-HybridSearch-001 — Búsqueda semántica con expansión por grafo
    Cuando busco "flujo de indexación de documentos" con strategy "hybrid" y expand_graph true
    Entonces los resultados incluyen "UC:UC-001" con match_source "semantic" o "fusion"
    Y los resultados incluyen "BR:BR-DOCUMENT-001" por expansión de grafo
    Y los resultados incluyen "CMD:CMD-001" por expansión de grafo
    Y el graph_expansion contiene edges entre los nodos devueltos
    Y los resultados están ordenados por score descendente
    Y la respuesta completa en menos de 300ms

  Escenario: SCN-HybridSearch-002 — Búsqueda con filtro por kind
    Cuando busco "reglas de negocio para documentos" con include_kinds ["business-rule"]
    Entonces todos los resultados tienen kind "business-rule"
    Y "BR:BR-DOCUMENT-001" aparece en los resultados

  Escenario: SCN-HybridSearch-003 — Búsqueda con respeto de capas
    Dado un edge con layer_violation de "Entity:X" (01-domain) a "UC:UC-001" (02-behavior)
    Cuando busco "entidad X" con respect_layers true
    Entonces "UC:UC-001" no aparece como resultado de expansión por grafo desde "Entity:X"

  Escenario: SCN-HybridSearch-004 — Degradación a grafo+lexical en índice L1
    Dado un índice L1 sin embeddings
    Cuando busco "indexación de documentos" con strategy "hybrid"
    Entonces la respuesta incluye warning "NO_EMBEDDINGS"
    Y los resultados provienen solo de grafo y lexical

  Escenario: SCN-HybridSearch-005 — Control de tokens
    Cuando busco "todo sobre pedidos" con max_tokens 1000
    Entonces el total_tokens de la respuesta no excede 1000
