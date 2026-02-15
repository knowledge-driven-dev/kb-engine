---
id: UC-001
kind: use-case
title: IndexDocument
version: 1
status: draft
actor: Developer
---

# UC-001 — IndexDocument

## Descripción

El desarrollador (o un git hook) solicita la indexación de un [[KDDDocument]] individual. El sistema ejecuta el pipeline completo: detecta el `kind` del documento, extrae el [[GraphNode]] y los [[GraphEdge|edges]], genera los [[Embedding|embeddings]] si el nivel de indexación lo permite, y almacena todo en `.kdd-index/`.

Este es el flujo atómico de indexación. Tanto la indexación completa como la incremental ([[UC-002-IndexIncremental]]) delegan en este caso de uso para cada documento individual.

## Actores

- **Developer**: Invoca la indexación manualmente (`kb index <file>`) o indirectamente via git hook.
- **Git Hook**: Trigger automático post-commit que invoca la indexación.

## Precondiciones

- El fichero existe dentro de `/specs` y es un archivo Markdown o YAML.
- El directorio `.kdd-index/` existe o puede crearse.
- El nivel de indexación ha sido determinado ([[BR-INDEX-001]]).

## Flujo Principal

1. El sistema recibe la ruta del fichero a indexar.
2. El sistema lee el fichero y extrae el front-matter YAML.
3. El sistema aplica [[BR-DOCUMENT-001]] para determinar el `kind` del documento. Se emite [[EVT-KDDDocument-Detected]].
4. El sistema selecciona el extractor correspondiente al `kind` y parsea el contenido: front-matter, secciones Markdown, wiki-links `[[...]]`. Se emite [[EVT-KDDDocument-Parsed]].
5. El sistema genera un [[GraphNode]] con los campos indexados según la tabla de nodos del PRD para ese `kind`.
6. El sistema extrae los [[GraphEdge|edges]]:
   - Cada wiki-link `[[Target]]` genera un edge `WIKI_LINK`.
   - Según el `kind` y la sección donde aparece cada wiki-link, se generan edges tipados (e.g. `UC_APPLIES_RULE`, `EMITS`).
   - Las relaciones de negocio en tablas `## Relaciones` generan edges en minúsculas.
7. El sistema valida cada edge contra [[BR-LAYER-001]] y marca `layer_violation: true` donde corresponda.
8. Si el nivel de indexación es ≥ L2 ([[BR-INDEX-001]]):
   - El sistema aplica [[BR-EMBEDDING-001]] para determinar las secciones embebibles.
   - Para cada sección embebible, aplica chunking jerárquico por párrafos.
   - Genera un [[Embedding]] por chunk usando el modelo configurado.
9. El sistema almacena nodo, edges y embeddings en `.kdd-index/`.
10. Se actualiza el [[IndexManifest]] con las estadísticas incrementadas.
11. Se emite [[EVT-KDDDocument-Indexed]] con métricas de duración.

## Flujos Alternativos

### FA-1: Documento sin front-matter
- En el paso 2, si el fichero no tiene front-matter YAML válido, el sistema lo ignora silenciosamente y termina. No se produce [[KDDDocument]] ni se emite ningún evento.

### FA-2: Kind no reconocido
- En el paso 3, si el `kind` del front-matter no es reconocido por [[BR-DOCUMENT-001]], el sistema registra un warning y termina. No se produce [[KDDDocument]].

### FA-3: Kind en ubicación inesperada
- En el paso 3, si el `kind` no coincide con la carpeta esperada, el sistema registra un warning pero continúa con el `kind` del front-matter (que tiene prioridad).

### FA-4: Degradación de nivel L2 → L1
- En el paso 8, si el modelo de embeddings falla (OOM, fichero corrupto), el sistema degrada a L1 ([[BR-INDEX-001]]), registra un warning, y continúa sin generar embeddings.

## Excepciones

### EX-1: Fichero no encontrado
- En el paso 1, si el fichero no existe, el sistema emite error `DOCUMENT_NOT_FOUND` y termina.

### EX-2: Error de extracción
- En el paso 4, si el extractor falla al parsear el contenido, se emite error `EXTRACTION_FAILED`. El [[KDDDocument]] queda en estado `detected` (reintentable).

### EX-3: Error de escritura en índice
- En el paso 9, si no se puede escribir en `.kdd-index/`, se emite error `INDEX_WRITE_FAILED`. Los artefactos generados se pierden.

## Postcondiciones

- Un [[GraphNode]] con id `{Kind}:{DocumentId}` existe en `.kdd-index/nodes/`.
- Los [[GraphEdge|edges]] del documento están en `.kdd-index/edges/edges.jsonl`.
- Si nivel ≥ L2: los [[Embedding|embeddings]] están en `.kdd-index/embeddings/`.
- El [[IndexManifest]] refleja el nuevo documento en sus `stats`.
- El tiempo de indexación del documento cumple el SLO de < 2s ([[REQ-001-Performance]]).

## Reglas Aplicadas

- [[BR-DOCUMENT-001]] — Kind Router: determina el `kind` y selecciona el extractor.
- [[BR-EMBEDDING-001]] — Embedding Strategy: determina qué secciones se embeben y aplica chunking jerárquico.
- [[BR-INDEX-001]] — Index Level: determina el nivel de indexación (L1/L2/L3).
- [[BR-LAYER-001]] — Layer Validation: valida dependencias de capa en cada edge generado.

## Comandos Ejecutados

- [[CMD-001-IndexDocument]] — Comando atómico que implementa este caso de uso.
