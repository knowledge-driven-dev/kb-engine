---
id: UC-007
kind: use-case
title: SyncIndex
version: 1
status: draft
actor: Developer
---

# UC-007 — SyncIndex

## Descripción

El desarrollador sincroniza sus artefactos de índice (`.kdd-index/`) con el servidor compartido. La sincronización tiene dos direcciones: **push** (subir índice local) y **pull** (descargar índice mergeado).

El push sube solo los artefactos derivados ([[GraphNode|nodos]], [[GraphEdge|edges]], [[Embedding|embeddings]], [[IndexManifest]]). El contenido original de las specs **nunca** se transmite, garantizando [[REQ-003-Privacy]].

## Actores

- **Developer**: Invoca `kb sync push` o `kb sync pull` explícitamente.
- **Git Hook**: Opcionalmente, un hook post-push puede invocar el sync automáticamente.

## Precondiciones

### Push
- Existe un [[IndexManifest]] local válido en `.kdd-index/`.
- El servidor o remoto es accesible.

### Pull
- El servidor tiene un índice mergeado disponible.
- El servidor o remoto es accesible.

## Flujo Principal

### Push

1. El desarrollador ejecuta `kb sync push`.
2. El sistema valida que existe un [[IndexManifest]] local válido.
3. El sistema empaqueta los artefactos de `.kdd-index/` (manifest, nodes, edges, embeddings, enrichments).
4. El sistema transmite los artefactos al servidor via el transporte configurado (`git` o `api`).
5. El servidor recibe los artefactos y los almacena, asociados al `indexed_by` del manifiesto.
6. Si hay índices de otros desarrolladores disponibles, el servidor puede disparar [[UC-006-MergeIndex]] automáticamente.

### Pull

1. El desarrollador ejecuta `kb sync pull`.
2. El sistema solicita al servidor el índice mergeado más reciente.
3. El servidor devuelve el [[IndexManifest]] mergeado con sus artefactos.
4. El sistema almacena los artefactos en `.kdd-index/` local, reemplazando el índice anterior.
5. Las consultas de retrieval locales operan ahora sobre el índice mergeado.

## Flujos Alternativos

### FA-1: Sin índice local (push)
- En el paso 2, si no existe índice local, se emite error `NO_LOCAL_INDEX`. El desarrollador debe ejecutar primero [[UC-001-IndexDocument]] o [[UC-002-IndexIncremental]].

### FA-2: Sin índice remoto (pull)
- En el paso 2 de pull, si el servidor no tiene índice mergeado disponible, se emite error `NO_REMOTE_INDEX`.

### FA-3: Transporte Git
- El push se implementa como `git add .kdd-index/ && git push`. El pull como `git pull` seguido de lectura de `.kdd-index/`.

### FA-4: Transporte API
- El push es un `POST /v1/index/push` con los artefactos como payload. El pull es un `GET /v1/index/pull`.

## Excepciones

### EX-1: Servidor inaccesible
- Se emite error `REMOTE_UNREACHABLE`. El índice local no se modifica.

### EX-2: Autenticación fallida
- Se emite error `AUTH_FAILED`. El desarrollador debe verificar sus credenciales.

### EX-3: Push rechazado
- El servidor puede rechazar el push si el manifiesto tiene una versión incompatible. Se emite error `PUSH_REJECTED`.

## Postcondiciones

### Push
- Los artefactos de índice local están disponibles en el servidor.
- El contenido original de las specs **no** se ha transmitido ([[REQ-003-Privacy]]).
- El servidor puede ejecutar merge con índices de otros desarrolladores.

### Pull
- El índice local contiene el grafo mergeado de todos los desarrolladores.
- Las consultas de retrieval locales reflejan el conocimiento de todo el equipo.

## Reglas Aplicadas

- [[BR-MERGE-001]] — Merge Conflict Resolution (aplicada por el servidor al mergear tras push).

## Comandos Ejecutados

- [[CMD-005-SyncIndex]] — Comando que implementa push/pull.
