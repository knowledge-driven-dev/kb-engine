---
id: UC-002
kind: use-case
title: IndexIncremental
version: 1
status: draft
actor: Developer
---

# UC-002 — IndexIncremental

## Descripción

El desarrollador hace commit de cambios en specs KDD y el sistema re-indexa automáticamente solo los documentos modificados, creados o eliminados. La detección de cambios se basa en `git diff` contra el commit registrado en el [[IndexManifest]].

Este es el flujo habitual en el día a día del desarrollador — la indexación se ejecuta en background tras cada commit, manteniendo el índice sincronizado con las specs.

## Actores

- **Developer**: Hace commit de cambios en specs.
- **Git Hook**: Trigger post-commit que invoca la indexación incremental.

## Precondiciones

- El directorio es un repositorio Git válido.
- Existe un [[IndexManifest]] previo en `.kdd-index/` con un `git_commit` registrado. Si no existe, se ejecuta una indexación completa.

## Flujo Principal

1. El git hook post-commit invoca `kb index --incremental`.
2. El sistema lee el `git_commit` del [[IndexManifest]] existente.
3. El sistema ejecuta `git diff --name-status {manifest.git_commit}..HEAD -- specs/` para obtener la lista de ficheros modificados.
4. Para cada fichero **nuevo** (status `A`):
   - El sistema ejecuta [[UC-001-IndexDocument]] para el fichero.
5. Para cada fichero **modificado** (status `M`):
   - El sistema emite [[EVT-KDDDocument-Stale]] para el documento afectado.
   - El sistema elimina el [[GraphNode]], [[GraphEdge|edges]] y [[Embedding|embeddings]] anteriores del documento.
   - El sistema ejecuta [[UC-001-IndexDocument]] para re-indexar el fichero.
6. Para cada fichero **eliminado** (status `D`):
   - El sistema emite [[EVT-KDDDocument-Deleted]].
   - El sistema elimina en cascada el [[GraphNode]], [[GraphEdge|edges]] y [[Embedding|embeddings]] asociados al documento.
7. El sistema actualiza el `git_commit` del [[IndexManifest]] a `HEAD`.
8. El sistema actualiza las `stats` del [[IndexManifest]] con los conteos resultantes.

## Flujos Alternativos

### FA-1: Sin índice previo
- En el paso 2, si no existe [[IndexManifest]], el sistema ejecuta una indexación completa de todos los ficheros en `/specs` (equivalente a ejecutar [[UC-001-IndexDocument]] para cada fichero), registra el `git_commit` de `HEAD`, y termina.

### FA-2: Sin cambios en specs
- En el paso 3, si `git diff` no devuelve ficheros dentro de `/specs`, el sistema termina sin hacer nada. El [[IndexManifest]] no se modifica.

### FA-3: Fichero renombrado
- En el paso 3, si `git diff` reporta un rename (status `R`), se trata como eliminación del path antiguo + creación del path nuevo.

## Excepciones

### EX-1: Repositorio Git no válido
- En el paso 2, si el directorio no es un repositorio Git, se emite error `GIT_NOT_AVAILABLE`.

### EX-2: Commit base no encontrado
- En el paso 3, si el `git_commit` del manifiesto ya no existe en el historial (e.g. rebase), se ejecuta indexación completa con warning.

### EX-3: Fallos parciales
- Si algunos documentos fallan al re-indexar (e.g. error de extracción), el sistema continúa con los demás y reporta `PARTIAL_FAILURE` al final con el conteo de errores.

## Postcondiciones

- Todos los documentos nuevos o modificados en el diff están indexados en `.kdd-index/`.
- Todos los documentos eliminados han sido eliminados del índice (nodo + edges + embeddings).
- El [[IndexManifest]] tiene `git_commit` = `HEAD` y `stats` actualizadas.
- El tiempo por documento cumple el SLO de < 2s ([[REQ-001-Performance]]).

## Reglas Aplicadas

- [[BR-DOCUMENT-001]] — Kind Router (delegado a [[UC-001-IndexDocument]]).
- [[BR-EMBEDDING-001]] — Embedding Strategy (delegado a [[UC-001-IndexDocument]]).
- [[BR-INDEX-001]] — Index Level (delegado a [[UC-001-IndexDocument]]).
- [[BR-LAYER-001]] — Layer Validation (delegado a [[UC-001-IndexDocument]]).

## Comandos Ejecutados

- [[CMD-002-IndexIncremental]] — Comando que orquesta la detección de cambios y delegación.
- [[CMD-001-IndexDocument]] — Invocado para cada documento individual.
