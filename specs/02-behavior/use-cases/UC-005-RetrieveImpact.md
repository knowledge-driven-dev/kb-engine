---
id: UC-005
kind: use-case
title: RetrieveImpact
version: 1
status: draft
actor: AIAgent
---

# UC-005 — RetrieveImpact

## Descripción

Un agente de IA o un desarrollador solicita un análisis de impacto sobre un [[GraphNode]] del grafo de conocimiento. El sistema recorre el grafo de dependencias para identificar todos los artefactos que se verían afectados por un cambio en el nodo consultado, incluyendo los scenarios BDD que deberían re-ejecutarse.

Este caso de uso es esencial para que los agentes entiendan las consecuencias de un cambio antes de ejecutarlo.

## Actores

- **AIAgent**: Solicita análisis de impacto antes de modificar una spec.
- **Developer**: Consulta impacto manualmente (`kb impact <node_id>`).

## Precondiciones

- El [[GraphNode]] consultado existe en el índice.
- Existe un índice cargado con edges suficientes para el traversal.

## Flujo Principal

1. El agente envía una [[RetrievalQuery]] con `strategy: impact` y un `root_node`. Se emite [[EVT-RetrievalQuery-Received]].
2. El sistema valida que el nodo existe en el índice.
3. El sistema identifica los nodos **directamente afectados**: todos los nodos conectados al nodo consultado por edges entrantes (nodos que dependen de él).
4. El sistema propaga el impacto **transitivamente**: para cada nodo directamente afectado, busca nodos que dependen de ellos, hasta la profundidad configurada.
5. Para cada nodo afectado, el sistema registra la cadena de dependencias (path de edges desde el nodo consultado hasta el nodo afectado).
6. El sistema busca BDD features (ficheros `.feature`) que validen alguno de los nodos afectados (via edges `VALIDATES`) y los incluye como scenarios a re-ejecutar.
7. El sistema construye el [[RetrievalResult]] con nodos directa e indirectamente afectados, paths de dependencia y scenarios.
8. Se emite [[EVT-RetrievalQuery-Completed]] con métricas.

## Flujos Alternativos

### FA-1: Nodo sin dependientes
- En el paso 3, si ningún nodo depende del nodo consultado (no tiene edges entrantes), el resultado contiene listas vacías. Esto es válido — el nodo es una "hoja" del grafo.

### FA-2: Profundidad limitada
- Si la propagación transitiva alcanza el `depth` máximo, se detiene. Los nodos más allá del límite no se incluyen pero se indica `truncated: true` en la respuesta.

## Excepciones

### EX-1: Nodo no encontrado
- En el paso 2, se emite [[EVT-RetrievalQuery-Failed]] con `NODE_NOT_FOUND`.

### EX-2: Índice no disponible
- Se emite [[EVT-RetrievalQuery-Failed]] con `INDEX_UNAVAILABLE`.

## Postcondiciones

- Un [[RetrievalResult]] con los nodos afectados ha sido devuelto.
- La respuesta incluye la cadena de dependencias para cada nodo afectado.
- Los BDD scenarios relevantes están identificados para re-ejecución.

## Reglas Aplicadas

- [[BR-LAYER-001]] — Layer Validation: las violaciones de capa se reportan en el análisis de impacto (un nodo con violación puede indicar una dependencia incorrecta).

## Comandos Ejecutados

- [[QRY-004-RetrieveImpact]] — Query que implementa el análisis de impacto.
- [[QRY-001-RetrieveByGraph]] — Usado internamente para el traversal de dependencias.
